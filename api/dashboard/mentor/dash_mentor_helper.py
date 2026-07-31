from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from db.user import UserMentor, MentorScopeGrant, MentorApplication
from db.organization import UserOrganizationLink
from db.task import InterestGroup, UserIgLink, TaskList, KarmaActivityLog
from db.mentor import MentorshipSession, IgOpportunity, SystemActionLog
from db.learning_circle import LearningCircle
from utils.utils import DateTimeUtils


CACHE_TTL = 15 * 60  # 15 minutes


def get_mentor_company(application):
    """
    Resolve an application's organization title.
    """
    if application.org:
        return application.org.title

    org_link = UserOrganizationLink.objects.filter(
        user=application.user, org__org_type="Company"
    ).select_related("org").first()
    return org_link.org.title if org_link else None


def get_mentor_scopes(user_id):
    """
    Return the set of active (scope_type, scope_id) pairs this user holds
    mentor authority over. This is the single deterministic source of truth
    for both authorization AND tier membership — a user's tiers are not
    stored anywhere on UserMentor, they are derived entirely from which
    MentorScopeGrant rows are active for them.
    """
    grants = MentorScopeGrant.objects.select_related('application').filter(
        application__user_id=user_id,
        application__status=MentorApplication.Status.APPROVED,
        is_active=True,
    ).values_list('scope_type', 'scope_id')
    return set(grants)


def has_scope(user_id, scope_type, scope_id=None):
    scope_id = str(scope_id) if scope_id is not None else None
    return (scope_type, scope_id) in get_mentor_scopes(user_id)


def get_scope_ids(user_id, scope_type):
    """All active scope_ids (org/ig ids) this user holds `scope_type` authority over."""
    return {sid for (st, sid) in get_mentor_scopes(user_id) if st == scope_type and sid}


def get_verified_company_for_mentor(user_id):
    """
    Resolve the verified Company a user may act on behalf of: either they are
    its registrant (company_user), or they hold an active COMPANY_MENTOR
    grant scoped to its Organization. Single source of truth for the
    previously-duplicated _get_company_for_user/get_verified_company helpers.
    """
    from db.company import Company
    from db.organization import Organization
    from db.user import MentorScopeGrant

    company = Company.objects.filter(company_user_id=user_id, status="verified").first()
    if company:
        return company

    org_ids = get_scope_ids(user_id, MentorScopeGrant.ScopeType.COMPANY_MENTOR)
    if not org_ids:
        return None
    org = Organization.objects.filter(id__in=org_ids).first()
    if not org:
        return None
    return Company.objects.filter(name=org.title, status="verified").first()


@transaction.atomic
def reconcile_mentor_ig_grants(application, actor_user_id):
    """
    Make the mentor's active IG_MENTOR MentorScopeGrant set exactly equal
    the (valid) preferred_ig_ids — the MentorScopeGrant counterpart to
    reconcile_mentor_ig_links. Only ever touches IG_MENTOR grants; any
    Company/Campus grant this mentor holds is untouched (grants are additive
    and independent per scope).
    """
    preferred_ig_ids = application.preferred_ig_ids
    desired = {str(i) for i in (preferred_ig_ids or []) if i}
    if desired:
        desired &= {
            str(x)
            for x in InterestGroup.objects.filter(id__in=desired).values_list(
                "id", flat=True
            )
        }

    ig_grants = list(
        MentorScopeGrant.objects.filter(
            application=application, scope_type=MentorScopeGrant.ScopeType.IG_MENTOR
        )
    )
    current_active = {g.scope_id for g in ig_grants if g.is_active}

    to_add = desired - current_active
    to_remove = current_active - desired
    now = DateTimeUtils.get_current_utc_time()

    for ig_id in to_add:
        existing = next((g for g in ig_grants if g.scope_id == ig_id), None)
        if existing:
            existing.is_active = True
            existing.revoked_by = None
            existing.revoked_at = None
            existing.save(update_fields=["is_active", "revoked_by", "revoked_at"])
        else:
            MentorScopeGrant.objects.create(
                application=application,
                scope_type=MentorScopeGrant.ScopeType.IG_MENTOR,
                scope_id=ig_id,
                is_active=True,
                granted_by_id=actor_user_id,
                granted_at=now,
            )

    if to_remove:
        MentorScopeGrant.objects.filter(
            application=application,
            scope_type=MentorScopeGrant.ScopeType.IG_MENTOR,
            scope_id__in=to_remove,
        ).update(is_active=False, revoked_by_id=actor_user_id, revoked_at=now)


@transaction.atomic
def reconcile_mentor_ig_links(user, preferred_ig_ids, actor_user_id):
    """
    Make the user's ACTIVE MENTOR UserIgLink set exactly equal the (valid)
    preferred_ig_ids: adds/reactivates links for newly chosen IGs and
    deactivates links for removed IGs.

    Only ever touches assignment_type=MENTOR rows — LEARNER/LEAD/MODERATOR
    links for the same IG are never modified. Used both for first-time admin
    approval and for self-service edits by already-approved IG mentors.

    Returns (added_ig_ids, removed_ig_ids) as sets of str.
    """
    desired = {str(i) for i in (preferred_ig_ids or []) if i}
    if desired:
        desired &= {
            str(x)
            for x in InterestGroup.objects.filter(id__in=desired).values_list(
                "id", flat=True
            )
        }

    mentor_links = list(
        UserIgLink.objects.filter(
            user=user, assignment_type=UserIgLink.AssignmentType.MENTOR
        )
    )
    current_active = {str(link.ig_id) for link in mentor_links if link.is_active}

    to_add = desired - current_active
    to_remove = current_active - desired
    now = DateTimeUtils.get_current_utc_time()

    for ig_id in to_add:
        existing = next((l for l in mentor_links if str(l.ig_id) == ig_id), None)
        if existing:
            existing.is_active = True
            existing.unassigned_at = None
            existing.assigned_by_id = actor_user_id
            existing.save(
                update_fields=["is_active", "unassigned_at", "assigned_by"]
            )
        else:
            UserIgLink.objects.create(
                user=user,
                ig_id=ig_id,
                assignment_type=UserIgLink.AssignmentType.MENTOR,
                is_active=True,
                assigned_by_id=actor_user_id,
                created_by_id=actor_user_id,
            )

    if to_remove:
        UserIgLink.objects.filter(
            user=user,
            assignment_type=UserIgLink.AssignmentType.MENTOR,
            ig_id__in=to_remove,
            is_active=True,
        ).update(is_active=False, unassigned_at=now)

    return to_add, to_remove

def get_mentor_overview(user_id):
        """
        Dynamically aggregates metrics based on the authenticated mentor's scope,
        derived entirely from their UserMentor record and UserIgLink.
        """
        active_scopes = []

        # 1. Campus and Company Scopes from UserMentor
        applications = MentorApplication.objects.filter(user_id=user_id, status=MentorApplication.Status.APPROVED).select_related('org')
        for app in applications:
            if app.mentor_tier == MentorApplication.MentorTier.CAMPUS_MENTOR and app.org_id:
                active_scopes.append({
                    "scope_type": "CAMPUS_MENTOR",
                    "scope_id": app.org_id,
                    "scope_name": app.org.title
                })
            elif app.mentor_tier == MentorApplication.MentorTier.COMPANY_MENTOR and app.org_id:
                active_scopes.append({
                    "scope_type": "COMPANY_MENTOR",
                    "scope_id": app.org_id,
                    "scope_name": app.org.title
                })

        # 2. IG Scopes from UserIgLink
        ig_links = UserIgLink.objects.filter(
            user_id=user_id, 
            assignment_type=UserIgLink.AssignmentType.MENTOR,
            is_active=True
        ).select_related('ig')
        
        for link in ig_links:
            active_scopes.append({
                "scope_type": "IG_MENTOR",
                "scope_id": link.ig_id,
                "scope_name": link.ig.name if link.ig else None
            })

        # Assemble metrics via Cache or Computation
        response_scopes = []
        for scope in active_scopes:
            cache_key = f"mentor_dash_scope:{scope['scope_type']}:{scope['scope_id']}"
            
            metrics = None
            try:
                metrics = cache.get(cache_key)
            except Exception:
                pass

            if metrics is None:
                if scope["scope_type"] == "CAMPUS_MENTOR":
                    metrics = _compute_campus_metrics(scope["scope_id"])
                elif scope["scope_type"] == "COMPANY_MENTOR":
                    metrics = _compute_company_metrics(scope["scope_id"])
                elif scope["scope_type"] == "IG_MENTOR":
                    metrics = _compute_ig_metrics(scope["scope_id"])
                
                if metrics is not None:
                    try:
                        cache.set(cache_key, metrics, CACHE_TTL)
                    except Exception:
                        pass

            scope["metrics"] = metrics or {}
            response_scopes.append(scope)

        return response_scopes

def _compute_campus_metrics(org_id):
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        total_learners = UserOrganizationLink.objects.filter(
            org_id=org_id, verified=True
        ).count()
        
        active_learners = UserOrganizationLink.objects.filter(
            org_id=org_id, 
            verified=True,
            user__wallet_user__karma_last_updated_at__gte=thirty_days_ago
        ).count()
        
        inactive_learners = total_learners - active_learners
        
        campus_learning_circles = LearningCircle.objects.filter(org_id=org_id).count()
        
        pending_task_reviews = KarmaActivityLog.objects.filter(
            user__user_organization_link_user__org_id=org_id, 
            mentor_review_status='PENDING'
        ).count()
        
        campus_tasks = TaskList.objects.filter(org_id=org_id, active=True).count()
        
        upcoming_sessions = MentorshipSession.objects.filter(
            entity_id=org_id,
            session_type=MentorshipSession.SessionType.CAMPUS_SESSION,
            starts_at__gt=timezone.now(),
            is_deleted=False
        ).exclude(status__in=[MentorshipSession.Status.CANCELLED, MentorshipSession.Status.REJECTED]).count()

        completed_sessions = MentorshipSession.objects.filter(
            entity_id=org_id,
            session_type=MentorshipSession.SessionType.CAMPUS_SESSION,
            status=MentorshipSession.Status.COMPLETED,
            is_deleted=False
        ).count()

        return {
            "total_learners": total_learners,
            "active_learners": active_learners,
            "inactive_learners": inactive_learners,
            "upcoming_sessions": upcoming_sessions,
            "completed_sessions": completed_sessions,
            "campus_learning_circles": campus_learning_circles,
            "pending_task_reviews": pending_task_reviews,
            "campus_tasks": campus_tasks
        }

def _compute_company_metrics(org_id):
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        total_assigned_learners = UserOrganizationLink.objects.filter(org_id=org_id).count()
        
        active_learners = UserOrganizationLink.objects.filter(
            org_id=org_id, 
            user__wallet_user__karma_last_updated_at__gte=thirty_days_ago
        ).count()
        
        inactive_learners = total_assigned_learners - active_learners
        
        gigs_tasks = TaskList.objects.filter(org_id=org_id, active=True).count()
        
        pending_appraisals = KarmaActivityLog.objects.filter(
            task__org_id=org_id, 
            mentor_review_status='PENDING'
        ).count()
        
        completed_appraisals = KarmaActivityLog.objects.filter(
            task__org_id=org_id, 
            mentor_review_status__in=['APPROVED', 'REJECTED']
        ).count()
        
        upcoming_sessions = MentorshipSession.objects.filter(
            entity_id=org_id,
            session_type=MentorshipSession.SessionType.COMPANY_SESSION,
            starts_at__gt=timezone.now(),
            is_deleted=False
        ).exclude(status__in=[MentorshipSession.Status.CANCELLED, MentorshipSession.Status.REJECTED]).count()

        completed_sessions = MentorshipSession.objects.filter(
            entity_id=org_id,
            session_type=MentorshipSession.SessionType.COMPANY_SESSION,
            status=MentorshipSession.Status.COMPLETED,
            is_deleted=False
        ).count()
        
        open_opportunities = IgOpportunity.objects.filter(org_id=org_id, status=IgOpportunity.Status.PUBLISHED).count()

        return {
            "total_assigned_learners": total_assigned_learners,
            "active_learners": active_learners,
            "inactive_learners": inactive_learners,
            "gigs_tasks": gigs_tasks,
            "pending_appraisals": pending_appraisals,
            "completed_appraisals": completed_appraisals,
            "upcoming_sessions": upcoming_sessions,
            "completed_sessions": completed_sessions,
            "open_opportunities": open_opportunities
        }

def _compute_ig_metrics(ig_id):
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        total_ig_learners = UserIgLink.objects.filter(
            ig_id=ig_id, 
            assignment_type=UserIgLink.AssignmentType.LEARNER,
            is_active=True
        ).count()
        
        active_ig_learners = UserIgLink.objects.filter(
            ig_id=ig_id, 
            assignment_type=UserIgLink.AssignmentType.LEARNER,
            is_active=True,
            user__wallet_user__karma_last_updated_at__gte=thirty_days_ago
        ).count()
        
        inactive_ig_learners = total_ig_learners - active_ig_learners
        
        ig_learning_circles = LearningCircle.objects.filter(ig_id=ig_id).count()
        open_opportunities = IgOpportunity.objects.filter(ig_id=ig_id, status=IgOpportunity.Status.PUBLISHED).count()
        ig_tasks = TaskList.objects.filter(ig_id=ig_id, active=True).count()

        upcoming_sessions = MentorshipSession.objects.filter(
            entity_id=ig_id,
            session_type=MentorshipSession.SessionType.IG_SESSION,
            starts_at__gt=timezone.now(),
            is_deleted=False
        ).exclude(status__in=[MentorshipSession.Status.CANCELLED, MentorshipSession.Status.REJECTED]).count()

        completed_sessions = MentorshipSession.objects.filter(
            entity_id=ig_id,
            session_type=MentorshipSession.SessionType.IG_SESSION,
            status=MentorshipSession.Status.COMPLETED,
            is_deleted=False
        ).count()

        pending_tasks = KarmaActivityLog.objects.filter(
            task__ig_id=ig_id, 
            mentor_review_status='PENDING'
        ).count()

        return {
            "total_ig_learners": total_ig_learners,
            "active_ig_learners": active_ig_learners,
            "inactive_ig_learners": inactive_ig_learners,
            "upcoming_sessions": upcoming_sessions,
            "completed_sessions": completed_sessions,
            "pending_tasks": pending_tasks,
            "ig_learning_circles": ig_learning_circles,
            "open_opportunities": open_opportunities,
            "ig_tasks": ig_tasks
        }
