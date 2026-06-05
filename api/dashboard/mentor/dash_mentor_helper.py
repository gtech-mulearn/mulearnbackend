from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from db.user import UserMentor
from db.organization import UserOrganizationLink
from db.task import UserIgLink, TaskList, KarmaActivityLog
from db.mentor import MentorshipSession, IgOpportunity
from db.learning_circle import LearningCircle


CACHE_TTL = 15 * 60  # 15 minutes

def get_mentor_overview(user_id):
        """
        Dynamically aggregates metrics based on the authenticated mentor's scope,
        derived entirely from their UserMentor record and UserIgLink.
        """
        active_scopes = []

        # 1. Campus and Company Scopes from UserMentor
        user_mentors = UserMentor.objects.filter(user_id=user_id, status=UserMentor.Status.APPROVED).select_related('org')
        for mentor in user_mentors:
            if mentor.mentor_tier == UserMentor.MentorTier.CAMPUS_MENTOR and mentor.org_id:
                active_scopes.append({
                    "scope_type": "CAMPUS_MENTOR",
                    "scope_id": mentor.org_id,
                    "scope_name": mentor.org.title
                })
            elif mentor.mentor_tier == UserMentor.MentorTier.COMPANY_MENTOR and mentor.org_id:
                active_scopes.append({
                    "scope_type": "COMPANY_MENTOR",
                    "scope_id": mentor.org_id,
                    "scope_name": mentor.org.title
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
