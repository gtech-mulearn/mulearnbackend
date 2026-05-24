from django.db.models import Count, F as models_F, Q, Sum, Value, IntegerField
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.views import APIView

from db.mentor import (
    IgOpportunity,
    MentorAvailabilitySlot,
    MentorKarmaAward,
    MentorshipSession,
    MentorshipSessionUserLink,
    SystemActionLog,
)
from db.mentor_task_request import MentorTaskRequest
from db.notification import Notification
from db.task import InterestGroup, KarmaActivityLog, TaskList, TaskType, UserIgLink
from db.user import Role, User, UserMentor, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils, DateTimeUtils

from .mentor_serializers import (
    GlobalSessionPendingSerializer,
    IgOpportunitySerializer,
    IgOpportunityWriteSerializer,
    KarmaReviewQueueSerializer,
    KarmaReviewSerializer,
    MentorAvailabilitySerializer,
    MentorAvailabilityWriteSerializer,
    MentorKarmaAwardSerializer,
    MentorKarmaAwardWriteSerializer,
    MentorLeaderboardSerializer,
    MentorListSerializer,
    MentorOnboardingSerializer,
    MentorOnboardingUpdateSerializer,
    MentorSessionCreateSerializer,
    MentorSessionDetailSerializer,
    MentorSessionListSerializer,
    MentorSessionParticipantAddSerializer,
    MentorSessionParticipantSerializer,
    MentorSessionStatusSerializer,
    MentorSessionUpdateSerializer,
    MentorTaskRequestCreateSerializer,
    MentorTaskRequestReviewSerializer,
    MentorTaskRequestSerializer,
    MentorVerifySerializer,
    SystemActionLogSerializer,
)

# ─── Role shorthand ──────────────────────────────────────────────────────────
ADMIN = RoleType.ADMIN.value
MENTOR = RoleType.MENTOR.value


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _log_action(action_type, actor_user_id, entity_name, entity_id,
                ig=None, subject_user=None, old_data=None, new_data=None, remarks=None):
    """Write a SystemActionLog row."""
    SystemActionLog.objects.create(
        action_type=action_type,
        actor_user_id=actor_user_id,
        subject_user=subject_user,
        ig=ig,
        entity_name=entity_name,
        entity_id=entity_id,
        old_data=old_data,
        new_data=new_data,
        remarks=remarks,
    )


def _is_ig_mentor_for(user_id: str, ig_id: str) -> bool:
    """True if the user is a verified IG_MENTOR actively linked to this IG."""
    return (
        UserMentor.objects.filter(
            user_id=user_id,
            is_verified=True,
            mentor_tier=UserMentor.MentorTier.IG_MENTOR,
        ).exists()
        and UserIgLink.objects.filter(
            user_id=user_id,
            ig_id=ig_id,
            assignment_type=UserIgLink.AssignmentType.MENTOR,
            is_active=True,
        ).exists()
    )


def _get_ig_lead_user_ids(ig_code: str) -> list:
    """Return user_ids of all active IG Leads for the given IG code."""
    return list(
        UserRoleLink.objects.filter(
            role__title=RoleType.IG_LEAD_ROLE(ig_code),
            is_active=True,
        ).values_list("user_id", flat=True)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Onboarding
# ─────────────────────────────────────────────────────────────────────────────

class MentorOnboardingAPI(APIView):
    """
    GET  — returns current user's UserMentor row (or 404)
    POST — apply to become a mentor (creates UserMentor)
    PATCH — update own about/expertise/reason
    """
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        mentor = UserMentor.objects.filter(user_id=user_id).select_related(
            "user", "verified_by"
        ).first()
        if not mentor:
            return CustomResponse(
                general_message="You have not applied to become a mentor yet."
            ).get_failure_response()

        serializer = MentorListSerializer(mentor)
        return CustomResponse(response={"mentor": serializer.data}).get_success_response()

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if UserMentor.objects.filter(user_id=user_id).exists():
            return CustomResponse(
                general_message="You have already applied to become a mentor."
            ).get_failure_response()

        data = request.data.copy()
        data["created_by"] = user_id
        data["updated_by"] = user_id

        serializer = MentorOnboardingSerializer(data=data)
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        mentor = serializer.save(user_id=user_id)
        return CustomResponse(
            general_message="Mentor application submitted successfully. Awaiting admin review.",
            response={"mentor": MentorListSerializer(mentor).data},
        ).get_success_response()

    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        mentor = UserMentor.objects.filter(user_id=user_id).first()
        if not mentor:
            return CustomResponse(
                general_message="Mentor profile not found."
            ).get_failure_response()

        data = request.data.copy()
        data["updated_by"] = user_id

        serializer = MentorOnboardingUpdateSerializer(
            data=data, instance=mentor, partial=True
        )
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        serializer.save()

        # If verified mentor added new preferred IGs → create pending UserIgLink + notify IG Leads
        if mentor.is_verified:
            new_ig_ids = data.get("preferred_ig_ids", [])
            if new_ig_ids:
                existing_ig_ids = set(
                    UserIgLink.objects.filter(
                        user_id=user_id,
                        assignment_type=UserIgLink.AssignmentType.MENTOR,
                    ).values_list("ig_id", flat=True)
                )
                for ig_uuid in new_ig_ids:
                    if ig_uuid in existing_ig_ids:
                        continue  # already linked (active or pending)
                    ig_obj = InterestGroup.objects.filter(id=ig_uuid).first()
                    if not ig_obj:
                        continue
                    # Create pending link (is_active=False = awaiting IG Lead approval)
                    UserIgLink.objects.get_or_create(
                        user_id=user_id,
                        ig_id=ig_uuid,
                        assignment_type=UserIgLink.AssignmentType.MENTOR,
                        defaults={
                            "is_active":    False,
                            "assigned_by_id": user_id,
                            "created_by_id": user_id,
                        },
                    )
                    # Notify all IG Leads of this IG
                    lead_ids = _get_ig_lead_user_ids(ig_obj.code)
                    for lead_id in lead_ids:
                        Notification.objects.create(
                            user_id=lead_id,
                            title=f"Mentor IG Link Request — {ig_obj.name}",
                            description=(
                                f"{mentor.user.full_name} has requested to be linked as a "
                                f"mentor for {ig_obj.name}. Please review and approve or reject."
                            ),
                            created_by_id=user_id,
                        )

        return CustomResponse(
            general_message="Mentor profile updated.",
            response={"mentor": MentorListSerializer(mentor).data},
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# Mentor List & Verify (Admin)
# ─────────────────────────────────────────────────────────────────────────────

class MentorListAPI(APIView):
    """GET — paginated list of all mentor applications (admin only)."""
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN])
    def get(self, request):
        is_verified = request.query_params.get("is_verified")
        mentor_qs = (
            UserMentor.objects
            .select_related("user", "verified_by")
            .all()
        )
        if is_verified is not None:
            mentor_qs = mentor_qs.filter(is_verified=is_verified.lower() == "true")

        paginated = CommonUtils.get_paginated_queryset(
            mentor_qs, request,
            search_fields=["user__full_name", "user__email", "user__muid"],
            sort_fields={
                "full_name": "user__full_name",
                "created_at": "created_at",
                "mentor_tier": "mentor_tier",
            },
        )
        serializer = MentorListSerializer(paginated["queryset"], many=True)
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated["pagination"]
        )


class MentorVerifyAPI(APIView):
    """
    PATCH /<mentor_id>/verify/

    Required body field:
        action : "approve" | "reject"

    Optional:
        note        : str  — shown to mentor in notification
        mentor_tier : "NORMAL" | "VERIFIED"  (approve only, default NORMAL)

    Approve:
        • is_verified = True, role assigned, IG links created, mentor notified ✅
    Reject:
        • user_mentor row deleted (user can reapply), mentor notified ❌
    """
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN])
    def patch(self, request, pk):
        admin_id = JWTUtils.fetch_user_id(request)
        mentor = UserMentor.objects.filter(id=pk).select_related("user").first()
        if not mentor:
            return CustomResponse(
                general_message="Mentor not found."
            ).get_failure_response()

        action = request.data.get("action", "").lower()
        note   = request.data.get("note", "")

        if action not in ("approve", "reject"):
            return CustomResponse(
                general_message="'action' must be 'approve' or 'reject'."
            ).get_failure_response()

        mentor_user = mentor.user  # cache before possible deletion

        # ── REJECT ─────────────────────────────────────────────────────────
        if action == "reject":
            mentor.delete()

            Notification.objects.create(
                user=mentor_user,
                title="Mentor Application Not Approved",
                description=(
                    f"Your mentor application was reviewed and not approved. "
                    f"Reason: {note}"
                    if note
                    else "Your mentor application was reviewed and not approved. "
                         "You may reapply after updating your profile."
                ),
                created_by_id=admin_id,
            )

            _log_action(
                action_type=SystemActionLog.ActionType.TASK_REVIEW,
                actor_user_id=admin_id,
                entity_name="user_mentor",
                entity_id=pk,
                subject_user=mentor_user,
                new_data={"action": "reject", "note": note},
            )

            return CustomResponse(
                general_message="Mentor application rejected. User notified and may reapply."
            ).get_success_response()

        # ── APPROVE ────────────────────────────────────────────────────────
        now         = DateTimeUtils.get_current_utc_time()
        mentor_tier = request.data.get("mentor_tier", UserMentor.MentorTier.IG_MENTOR)

        mentor.is_verified       = True
        mentor.verified_by_id    = admin_id
        mentor.verified_at       = now
        mentor.verification_note = note
        mentor.mentor_tier       = mentor_tier
        mentor.updated_by_id     = admin_id
        mentor.save()

        # Assign Mentor role (idempotent)
        mentor_role = Role.objects.filter(title=RoleType.MENTOR.value).first()
        if mentor_role:
            already_has_role = UserRoleLink.objects.filter(
                user_id=mentor.user_id,
                role=mentor_role,
                is_active=True,
            ).exists()
            if not already_has_role:
                UserRoleLink.objects.create(
                    user_id=mentor.user_id,
                    role=mentor_role,
                    verified=True,
                    created_by_id=admin_id,
                )

        # Create UserIgLink rows for preferred IGs (Feature 5)
        if mentor.preferred_ig_ids:
            for ig_uuid in mentor.preferred_ig_ids:
                if InterestGroup.objects.filter(id=ig_uuid).exists():
                    UserIgLink.objects.get_or_create(
                        user_id=mentor.user_id,
                        ig_id=ig_uuid,
                        assignment_type=UserIgLink.AssignmentType.MENTOR,
                        defaults={
                            "assigned_by_id": admin_id,
                            "created_by_id":  admin_id,
                        },
                    )

        # Notify mentor of approval
        Notification.objects.create(
            user=mentor_user,
            title="🎉 Mentor Application Approved!",
            description=(
                f"Congratulations! Your mentor application has been approved. "
                f"You are now a {mentor_tier.capitalize()} mentor on muLearn."
            ),
            created_by_id=admin_id,
        )

        _log_action(
            action_type=SystemActionLog.ActionType.TASK_REVIEW,
            actor_user_id=admin_id,
            entity_name="user_mentor",
            entity_id=pk,
            subject_user=mentor_user,
            new_data={"action": "approve", "mentor_tier": mentor_tier},
        )

        return CustomResponse(
            general_message="Mentor application approved. Mentor role assigned.",
            response={"mentor": MentorListSerializer(mentor).data},
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# Overview (rich single-call dashboard snapshot)
# ─────────────────────────────────────────────────────────────────────────────

class MentorOverviewAPI(APIView):
    """
    GET /mentor/overview/

    Returns a comprehensive dashboard snapshot in a single call.
    Admin sees platform-wide data; mentor sees their own scoped data.

    Optional query param: ?ig_id=<id>  — scope session/opportunity counts to one IG.

    Response shape:
    {
      "mentors": { total, verified, unverified, pending_verification },
      "sessions": {
        "counts": { pending_approval, scheduled, completed, cancelled, no_show, total },
        "upcoming": [ ...next 5 SCHEDULED sessions ],
        "pending_global": [ ...next 5 PENDING_APPROVAL global sessions ]
      },
      "task_requests": { pending, approved, rejected,
                         recent_pending: [ ...latest 5 PENDING requests ] },
      "opportunities": { total, published, draft, closed,
                         by_ig: [ { ig_id, ig_name, count } ] },
      "mentees": { total_unique },
      "recent_activity": [ ...last 5 SystemActionLog entries ]
    }
    """
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        is_admin = ADMIN in roles
        ig_id = request.query_params.get("ig_id")
        now = DateTimeUtils.get_current_utc_time()

        # ── 1. Mentor counts (admin-only; mentor sees own status) ──────────────
        if is_admin:
            total_mentors = UserMentor.objects.count()
            verified_mentors = UserMentor.objects.filter(is_verified=True).count()
            unverified_mentors = total_mentors - verified_mentors
            pending_verification = UserMentor.objects.filter(
                is_verified=False
            ).count()
            mentor_info = {
                "total": total_mentors,
                "verified": verified_mentors,
                "unverified": unverified_mentors,
                "pending_verification": pending_verification,
            }
        else:
            own = UserMentor.objects.filter(user_id=user_id).first()
            mentor_info = {
                "is_verified": own.is_verified if own else False,
                "mentor_tier": own.mentor_tier if own else None,
                "hours": own.hours if own else 0,
            }

        # ── 2. Session counts ─────────────────────────────────────────────────
        session_qs = MentorshipSession.objects.all()
        if ig_id:
            session_qs = session_qs.filter(ig_id=ig_id)
        if not is_admin:
            # Mentor sees only sessions they're linked to
            session_qs = session_qs.filter(
                participants__user_id=user_id
            ).distinct()

        status_counts = {
            item["status"]: item["count"]
            for item in session_qs.values("status").annotate(count=Count("id"))
        }
        session_total = sum(status_counts.values())

        # Upcoming: next 5 SCHEDULED sessions ordered by starts_at
        upcoming_qs = (
            session_qs
            .filter(status=MentorshipSession.Status.SCHEDULED, starts_at__gte=now)
            .select_related("ig", "created_by")
            .order_by("starts_at")[:5]
        )
        upcoming = MentorSessionListSerializer(upcoming_qs, many=True).data

        # Pending global sessions (admin only)
        pending_global = []
        if is_admin:
            pending_global_qs = (
                MentorshipSession.objects
                .filter(is_global=True, status=MentorshipSession.Status.PENDING_APPROVAL)
                .select_related("ig", "created_by")
                .order_by("created_at")[:5]
            )
            pending_global = MentorSessionListSerializer(pending_global_qs, many=True).data

        session_info = {
            "counts": {
                "pending_approval": status_counts.get(MentorshipSession.Status.PENDING_APPROVAL, 0),
                "scheduled": status_counts.get(MentorshipSession.Status.SCHEDULED, 0),
                "completed": status_counts.get(MentorshipSession.Status.COMPLETED, 0),
                "cancelled": status_counts.get(MentorshipSession.Status.CANCELLED, 0),
                "no_show": status_counts.get(MentorshipSession.Status.NO_SHOW, 0),
                "total": session_total,
            },
            "upcoming": upcoming,
            "pending_global": pending_global,
        }

        # ── 3. Task requests ──────────────────────────────────────────────────
        tr_qs = MentorTaskRequest.objects.all()
        if not is_admin:
            tr_qs = tr_qs.filter(mentor_id=user_id)
        if ig_id:
            tr_qs = tr_qs.filter(ig_id=ig_id)

        tr_counts = {
            item["status"]: item["count"]
            for item in tr_qs.values("status").annotate(count=Count("id"))
        }
        recent_pending_tr = (
            tr_qs
            .filter(status=MentorTaskRequest.Status.PENDING)
            .select_related("mentor", "ig")
            .order_by("-created_at")[:5]
        )
        task_request_info = {
            "pending": tr_counts.get(MentorTaskRequest.Status.PENDING, 0),
            "approved": tr_counts.get(MentorTaskRequest.Status.APPROVED, 0),
            "rejected": tr_counts.get(MentorTaskRequest.Status.REJECTED, 0),
            "recent_pending": MentorTaskRequestSerializer(recent_pending_tr, many=True).data,
        }

        # ── 4. Opportunities ──────────────────────────────────────────────────
        opp_qs = IgOpportunity.objects.all()
        if ig_id:
            opp_qs = opp_qs.filter(ig_id=ig_id)

        opp_status_counts = {
            item["status"]: item["count"]
            for item in opp_qs.values("status").annotate(count=Count("id"))
        }

        # Per-IG breakdown (top 10 IGs by opportunity count)
        opp_by_ig = list(
            opp_qs
            .values("ig_id", "ig__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        opportunity_info = {
            "total": sum(opp_status_counts.values()),
            "published": opp_status_counts.get(IgOpportunity.Status.PUBLISHED, 0),
            "draft": opp_status_counts.get(IgOpportunity.Status.DRAFT, 0),
            "closed": opp_status_counts.get(IgOpportunity.Status.CLOSED, 0),
            "by_ig": [
                {"ig_id": r["ig_id"], "ig_name": r["ig__name"], "count": r["count"]}
                for r in opp_by_ig
            ],
        }

        # ── 5. Unique mentees ─────────────────────────────────────────────────
        mentee_session_ids = session_qs.values_list("id", flat=True)
        unique_mentees = (
            MentorshipSessionUserLink.objects
            .filter(
                session_id__in=mentee_session_ids,
                participant_role=MentorshipSessionUserLink.ParticipantRole.MENTEE,
            )
            .values("user_id")
            .distinct()
            .count()
        )

        # ── 6. Recent activity (last 5 log entries) ───────────────────────────
        log_qs = (
            SystemActionLog.objects
            .select_related("actor_user", "subject_user", "ig")
            .order_by("-created_at")
        )
        if not is_admin:
            log_qs = log_qs.filter(actor_user_id=user_id)
        if ig_id:
            log_qs = log_qs.filter(ig_id=ig_id)

        recent_activity = SystemActionLogSerializer(log_qs[:5], many=True).data

        # ── Assemble final response ───────────────────────────────────────────
        overview = {
            "mentors": mentor_info,
            "sessions": session_info,
            "task_requests": task_request_info,
            "opportunities": opportunity_info,
            "mentees": {"total_unique": unique_mentees},
            "recent_activity": recent_activity,
        }
        return CustomResponse(response={"overview": overview}).get_success_response()


# Kept for backwards-compatibility — just delegates to overview
class MentorStatsAPI(MentorOverviewAPI):
    """Alias: GET /mentor/stats/ → same as /mentor/overview/."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Sessions
# ─────────────────────────────────────────────────────────────────────────────

class MentorSessionAPI(APIView):
    """
    GET  — paginated session list (admin sees all; mentor sees own)
    POST — create session:
           • with ig_id  → admin only, status=SCHEDULED
           • without ig_id → mentor/admin, status=PENDING_APPROVAL, is_global=True
    """
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        is_admin = ADMIN in roles

        session_qs = (
            MentorshipSession.objects
            .select_related("ig", "created_by", "updated_by")
            .prefetch_related("participants")
        )

        if not is_admin:
            # Mentors only see sessions they're linked to
            session_qs = session_qs.filter(
                participants__user_id=user_id
            ).distinct()

        # Optional filters
        ig_id = request.query_params.get("ig_id")
        status_filter = request.query_params.get("status")
        is_global = request.query_params.get("is_global")

        if ig_id:
            session_qs = session_qs.filter(ig_id=ig_id)
        if status_filter:
            session_qs = session_qs.filter(status=status_filter)
        if is_global is not None:
            session_qs = session_qs.filter(is_global=is_global.lower() == "true")

        paginated = CommonUtils.get_paginated_queryset(
            session_qs, request,
            search_fields=["title", "ig__name"],
            sort_fields={
                "title": "title",
                "starts_at": "starts_at",
                "status": "status",
                "created_at": "created_at",
            },
        )
        serializer = MentorSessionListSerializer(paginated["queryset"], many=True)
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated["pagination"]
        )

    @role_required([ADMIN, MENTOR])
    def post(self, request):
        user_id  = JWTUtils.fetch_user_id(request)
        roles    = JWTUtils.fetch_role(request)
        is_admin = ADMIN in roles

        ig_id      = request.data.get("ig")
        is_global  = not ig_id  # no IG supplied → treat as global

        if not is_admin:
            mentor = UserMentor.objects.filter(user_id=user_id, is_verified=True).first()
            if not mentor:
                return CustomResponse(
                    general_message="A verified mentor profile is required to create sessions."
                ).get_failure_response()

            if mentor.mentor_tier == UserMentor.MentorTier.IG_MENTOR:
                if ig_id:
                    # IG session — must be linked to that IG
                    if not _is_ig_mentor_for(user_id, ig_id):
                        return CustomResponse(
                            general_message="You are not an IG Mentor for this interest group."
                        ).get_failure_response()
                    is_global = False
                else:
                    # IG_MENTOR creating a global session — allowed, goes to PENDING_APPROVAL
                    is_global = True

            elif mentor.mentor_tier == UserMentor.MentorTier.MENTOR:
                if ig_id:
                    return CustomResponse(
                        general_message="Global Mentors cannot create IG-scoped sessions."
                    ).get_failure_response()
                is_global = True

        # Validate IG exists if provided
        if ig_id and not InterestGroup.objects.filter(id=ig_id).exists():
            return CustomResponse(
                general_message="Interest Group not found."
            ).get_failure_response()

        data = request.data.copy()
        data["created_by"] = user_id
        data["updated_by"] = user_id
        data["is_global"]  = is_global
        data["status"] = (
            MentorshipSession.Status.PENDING_APPROVAL
            if is_global
            else MentorshipSession.Status.SCHEDULED
        )

        serializer = MentorSessionCreateSerializer(data=data)
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        session = serializer.save()

        # Auto-add creator as MENTOR participant
        MentorshipSessionUserLink.objects.create(
            session=session,
            user_id=user_id,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
            attendance_status=MentorshipSessionUserLink.AttendanceStatus.INVITED,
        )

        _log_action(
            action_type=SystemActionLog.ActionType.SESSION_CREATE,
            actor_user_id=user_id,
            entity_name="mentorship_session",
            entity_id=session.id,
            ig=session.ig,
            new_data={"title": session.title, "is_global": session.is_global},
        )

        return CustomResponse(
            general_message=(
                "Global session submitted for admin approval."
                if is_global
                else "Session created successfully."
            ),
            response={"session": MentorSessionDetailSerializer(session).data},
        ).get_success_response()


class MentorSessionDetailAPI(APIView):
    """GET / PUT / PATCH / DELETE for a single session."""
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def get(self, request, pk):
        session = (
            MentorshipSession.objects
            .select_related("ig", "created_by", "updated_by", "approved_by")
            .prefetch_related("participants__user")
            .filter(id=pk)
            .first()
        )
        if not session:
            return CustomResponse(general_message="Session not found.").get_failure_response()

        serializer = MentorSessionDetailSerializer(session)
        return CustomResponse(response={"session": serializer.data}).get_success_response()

    @role_required([ADMIN, MENTOR])
    def patch(self, request, pk):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        is_admin = ADMIN in roles

        session = MentorshipSession.objects.filter(id=pk).first()
        if not session:
            return CustomResponse(general_message="Session not found.").get_failure_response()

        # Mentor can only edit sessions they created
        if not is_admin and str(session.created_by_id) != user_id:
            return CustomResponse(
                general_message="You can only edit sessions you created."
            ).get_failure_response()

        old_data = MentorSessionDetailSerializer(session).data

        data = request.data.copy()
        data["updated_by"] = user_id

        serializer = MentorSessionUpdateSerializer(data=data, instance=session, partial=True)
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        serializer.save()

        _log_action(
            action_type=SystemActionLog.ActionType.SESSION_UPDATE,
            actor_user_id=user_id,
            entity_name="mentorship_session",
            entity_id=session.id,
            ig=session.ig,
            old_data=dict(old_data),
            new_data=request.data,
        )

        return CustomResponse(
            general_message="Session updated.",
            response={"session": MentorSessionDetailSerializer(session).data},
        ).get_success_response()

    @role_required([ADMIN])
    def delete(self, request, pk):
        user_id = JWTUtils.fetch_user_id(request)
        session = MentorshipSession.objects.filter(id=pk).first()
        if not session:
            return CustomResponse(general_message="Session not found.").get_failure_response()

        session.status = MentorshipSession.Status.CANCELLED
        session.updated_by_id = user_id
        session.save()

        _log_action(
            action_type=SystemActionLog.ActionType.SESSION_STATUS,
            actor_user_id=user_id,
            entity_name="mentorship_session",
            entity_id=session.id,
            ig=session.ig,
            new_data={"status": MentorshipSession.Status.CANCELLED},
            remarks="Deleted by admin — status set to CANCELLED",
        )

        return CustomResponse(
            general_message="Session cancelled successfully."
        ).get_success_response()


class MentorSessionStatusAPI(APIView):
    """PATCH — update only the session status (admin only)."""
    authentication_classes = [CustomizePermission]

    ALLOWED_TRANSITIONS = {
        MentorshipSession.Status.SCHEDULED: [
            MentorshipSession.Status.COMPLETED,
            MentorshipSession.Status.CANCELLED,
            MentorshipSession.Status.NO_SHOW,
        ],
        MentorshipSession.Status.COMPLETED: [],
        MentorshipSession.Status.CANCELLED: [],
        MentorshipSession.Status.NO_SHOW: [],
        MentorshipSession.Status.PENDING_APPROVAL: [],  # use /approve/ endpoint instead
    }

    @role_required([ADMIN])
    def patch(self, request, pk):
        user_id = JWTUtils.fetch_user_id(request)
        session = MentorshipSession.objects.filter(id=pk).first()
        if not session:
            return CustomResponse(general_message="Session not found.").get_failure_response()

        new_status = request.data.get("status")
        if not new_status:
            return CustomResponse(general_message="'status' field is required.").get_failure_response()

        if new_status == MentorshipSession.Status.PENDING_APPROVAL:
            return CustomResponse(
                general_message="Use the /approve/ endpoint to manage pending global sessions."
            ).get_failure_response()

        allowed = self.ALLOWED_TRANSITIONS.get(session.status, [])
        if new_status not in allowed:
            return CustomResponse(
                general_message=f"Cannot transition from '{session.status}' to '{new_status}'."
            ).get_failure_response()

        data = {"status": new_status, "updated_by": user_id}
        serializer = MentorSessionStatusSerializer(data=data, instance=session, partial=True)
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        serializer.save()

        _log_action(
            action_type=SystemActionLog.ActionType.SESSION_STATUS,
            actor_user_id=user_id,
            entity_name="mentorship_session",
            entity_id=session.id,
            ig=session.ig,
            new_data={"status": new_status},
        )

        return CustomResponse(
            general_message=f"Session status updated to '{new_status}'."
        ).get_success_response()


class MentorSessionParticipantsAPI(APIView):
    """GET / POST / DELETE participants on a session."""
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def get(self, request, pk):
        session = MentorshipSession.objects.filter(id=pk).first()
        if not session:
            return CustomResponse(general_message="Session not found.").get_failure_response()

        participants = (
            MentorshipSessionUserLink.objects
            .filter(session_id=pk)
            .select_related("user")
        )
        serializer = MentorSessionParticipantSerializer(participants, many=True)
        return CustomResponse(
            response={"participants": serializer.data}
        ).get_success_response()

    @role_required([ADMIN, MENTOR])
    def post(self, request, pk):
        user_id = JWTUtils.fetch_user_id(request)
        session = MentorshipSession.objects.filter(id=pk).first()
        if not session:
            return CustomResponse(general_message="Session not found.").get_failure_response()

        data = request.data.copy()
        data["session"] = pk

        # Validate participant user exists
        participant_user_id = data.get("user")
        if not User.objects.filter(id=participant_user_id).exists():
            return CustomResponse(
                general_message="Participant user not found."
            ).get_failure_response()

        # Check for duplicate
        role = data.get("participant_role")
        if MentorshipSessionUserLink.objects.filter(
            session_id=pk, user_id=participant_user_id, participant_role=role
        ).exists():
            return CustomResponse(
                general_message="This user already has this role in the session."
            ).get_failure_response()

        serializer = MentorSessionParticipantAddSerializer(data=data)
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        link = serializer.save()
        return CustomResponse(
            general_message="Participant added.",
            response={"participant": MentorSessionParticipantSerializer(link).data},
        ).get_success_response()

    @role_required([ADMIN, MENTOR])
    def delete(self, request, pk, user_pk):
        MentorshipSessionUserLink.objects.filter(
            session_id=pk, user_id=user_pk
        ).delete()
        return CustomResponse(
            general_message="Participant removed."
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# Global Session Approval Queue
# ─────────────────────────────────────────────────────────────────────────────

class GlobalSessionPendingAPI(APIView):
    """GET — paginated list of global sessions awaiting admin approval."""
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN])
    def get(self, request):
        pending_qs = (
            MentorshipSession.objects
            .filter(is_global=True, status=MentorshipSession.Status.PENDING_APPROVAL)
            .select_related("ig", "created_by")
        )
        paginated = CommonUtils.get_paginated_queryset(
            pending_qs, request,
            search_fields=["title", "created_by__full_name"],
            sort_fields={"title": "title", "created_at": "created_at"},
        )

        # Feature 6: compute keyword-based IG suggestions for each session
        all_igs = list(
            InterestGroup.objects.filter(status="active")
            .values("id", "name", "about")
        )

        def _suggest_igs(session, igs, top_n=3):
            keywords = set(
                (session.title + " " + (session.description or "")).lower().split()
            )
            keywords = {w for w in keywords if len(w) > 3}  # skip short words
            scored = []
            for ig in igs:
                ig_text = ((ig["name"] or "") + " " + (ig["about"] or "")).lower()
                score = sum(1 for kw in keywords if kw in ig_text)
                if score > 0:
                    scored.append({"ig_id": ig["id"], "ig_name": ig["name"], "score": score})
            scored.sort(key=lambda x: x["score"], reverse=True)
            return [{"ig_id": s["ig_id"], "ig_name": s["ig_name"]} for s in scored[:top_n]]

        ig_suggestions = {
            s.id: _suggest_igs(s, all_igs)
            for s in paginated["queryset"]
        }

        serializer = GlobalSessionPendingSerializer(
            paginated["queryset"], many=True,
            context={"ig_suggestions": ig_suggestions}
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated["pagination"]
        )


class GlobalSessionApproveAPI(APIView):
    """PATCH — admin approves or rejects a pending global session."""
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN])
    def patch(self, request, pk):
        admin_id = JWTUtils.fetch_user_id(request)
        session = MentorshipSession.objects.filter(id=pk).first()
        if not session:
            return CustomResponse(general_message="Session not found.").get_failure_response()

        if not session.is_global:
            return CustomResponse(
                general_message="This endpoint is only for global sessions."
            ).get_failure_response()

        if session.status != MentorshipSession.Status.PENDING_APPROVAL:
            return CustomResponse(
                general_message=f"Session is already '{session.status}', not pending approval."
            ).get_failure_response()

        action = request.data.get("action", "").lower()
        remarks = request.data.get("remarks", "")
        # Feature 6: optional ig_id to convert global → IG-scoped on approve
        convert_ig_id = request.data.get("ig_id")

        if action == "approve":
            new_status = MentorshipSession.Status.SCHEDULED
            message = "Global session approved and scheduled."
        elif action == "reject":
            new_status = MentorshipSession.Status.CANCELLED
            message = "Global session rejected."
        else:
            return CustomResponse(
                general_message="'action' must be 'approve' or 'reject'."
            ).get_failure_response()

        # Optionally attach an IG (converts global → IG-scoped)
        if action == "approve" and convert_ig_id:
            if not InterestGroup.objects.filter(id=convert_ig_id).exists():
                return CustomResponse(
                    general_message="Provided ig_id does not exist."
                ).get_failure_response()
            session.ig_id = convert_ig_id
            session.is_global = False

        now = DateTimeUtils.get_current_utc_time()
        session.status = new_status
        session.approved_by_id = admin_id
        session.approved_at = now
        session.updated_by_id = admin_id
        session.save()

        _log_action(
            action_type=SystemActionLog.ActionType.SESSION_STATUS,
            actor_user_id=admin_id,
            entity_name="mentorship_session",
            entity_id=session.id,
            new_data={"status": new_status, "action": action},
            remarks=remarks or None,
        )

        return CustomResponse(
            general_message=message,
            response={"session": MentorSessionDetailSerializer(session).data},
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# Availability
# ─────────────────────────────────────────────────────────────────────────────

class MentorAvailabilityAPI(APIView):
    """GET — list slots; POST — create a new slot."""
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        is_admin = ADMIN in roles

        mentor_user_id = request.query_params.get("mentor_user_id")
        ig_id = request.query_params.get("ig_id")

        slot_qs = (
            MentorAvailabilitySlot.objects
            .filter(is_active=True)
            .select_related("mentor_user", "ig")
        )

        if not is_admin:
            slot_qs = slot_qs.filter(mentor_user_id=user_id)
        elif mentor_user_id:
            slot_qs = slot_qs.filter(mentor_user_id=mentor_user_id)

        if ig_id:
            slot_qs = slot_qs.filter(ig_id=ig_id)

        paginated = CommonUtils.get_paginated_queryset(
            slot_qs, request,
            search_fields=["mentor_user__full_name"],
            sort_fields={"weekday": "weekday", "start_time": "start_time"},
        )
        serializer = MentorAvailabilitySerializer(paginated["queryset"], many=True)
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated["pagination"]
        )

    @role_required([MENTOR])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        data = request.data.copy()
        data["mentor_user"] = user_id
        data["created_by"] = user_id
        data["updated_by"] = user_id

        serializer = MentorAvailabilityWriteSerializer(data=data)
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        slot = serializer.save()
        return CustomResponse(
            general_message="Availability slot created.",
            response={"slot": MentorAvailabilitySerializer(slot).data},
        ).get_success_response()


class MentorAvailabilityDetailAPI(APIView):
    """PUT — full replace; DELETE — soft-delete."""
    authentication_classes = [CustomizePermission]

    @role_required([MENTOR])
    def put(self, request, pk):
        user_id = JWTUtils.fetch_user_id(request)
        slot = MentorAvailabilitySlot.objects.filter(
            id=pk, mentor_user_id=user_id
        ).first()
        if not slot:
            return CustomResponse(
                general_message="Slot not found or does not belong to you."
            ).get_failure_response()

        data = request.data.copy()
        data["mentor_user"] = user_id
        data["updated_by"] = user_id
        data["created_by"] = user_id  # required by serializer

        serializer = MentorAvailabilityWriteSerializer(data=data, instance=slot)
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        serializer.save()
        return CustomResponse(
            general_message="Availability slot updated.",
            response={"slot": MentorAvailabilitySerializer(slot).data},
        ).get_success_response()

    @role_required([ADMIN, MENTOR])
    def delete(self, request, pk):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        is_admin = ADMIN in roles

        slot_qs = MentorAvailabilitySlot.objects.filter(id=pk)
        if not is_admin:
            slot_qs = slot_qs.filter(mentor_user_id=user_id)

        slot = slot_qs.first()
        if not slot:
            return CustomResponse(
                general_message="Slot not found."
            ).get_failure_response()

        slot.is_active = False
        slot.updated_by_id = user_id
        slot.save()
        return CustomResponse(
            general_message="Availability slot deactivated."
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# Task Requests
# ─────────────────────────────────────────────────────────────────────────────

class MentorTaskRequestAPI(APIView):
    """GET — list; POST — submit a task proposal."""
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        is_admin = ADMIN in roles

        status_filter = request.query_params.get("status")
        qs = MentorTaskRequest.objects.select_related(
            "mentor", "ig", "reviewed_by", "created_task"
        )

        if not is_admin:
            qs = qs.filter(mentor_id=user_id)
        if status_filter:
            qs = qs.filter(status=status_filter)

        paginated = CommonUtils.get_paginated_queryset(
            qs, request,
            search_fields=["title", "hashtag", "mentor__full_name", "ig__name"],
            sort_fields={
                "title": "title",
                "status": "status",
                "created_at": "created_at",
            },
        )
        serializer = MentorTaskRequestSerializer(paginated["queryset"], many=True)
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated["pagination"]
        )

    @role_required([MENTOR])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        data = request.data.copy()
        data["mentor"] = user_id
        data["created_by"] = user_id
        data["updated_by"] = user_id

        serializer = MentorTaskRequestCreateSerializer(data=data)
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        task_req = serializer.save()
        return CustomResponse(
            general_message="Task proposal submitted. Awaiting admin review.",
            response={"task_request": MentorTaskRequestSerializer(task_req).data},
        ).get_success_response()


class MentorTaskRequestDetailAPI(APIView):
    """GET — detail; PATCH — admin review (approve/reject)."""
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def get(self, request, pk):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        is_admin = ADMIN in roles

        qs = MentorTaskRequest.objects.select_related(
            "mentor", "ig", "reviewed_by", "created_task"
        ).filter(id=pk)

        if not is_admin:
            qs = qs.filter(mentor_id=user_id)

        task_req = qs.first()
        if not task_req:
            return CustomResponse(
                general_message="Task request not found."
            ).get_failure_response()

        return CustomResponse(
            response={"task_request": MentorTaskRequestSerializer(task_req).data}
        ).get_success_response()

    @role_required([ADMIN])
    def patch(self, request, pk):
        admin_id = JWTUtils.fetch_user_id(request)
        task_req = MentorTaskRequest.objects.select_related(
            "mentor", "ig"
        ).filter(id=pk).first()
        if not task_req:
            return CustomResponse(
                general_message="Task request not found."
            ).get_failure_response()

        if task_req.status != MentorTaskRequest.Status.PENDING:
            return CustomResponse(
                general_message=f"This request is already '{task_req.status}'."
            ).get_failure_response()

        new_status = request.data.get("status")
        if new_status not in [MentorTaskRequest.Status.APPROVED, MentorTaskRequest.Status.REJECTED]:
            return CustomResponse(
                general_message="Status must be 'APPROVED' or 'REJECTED'."
            ).get_failure_response()

        now = DateTimeUtils.get_current_utc_time()
        data = {
            "status": new_status,
            "admin_note": request.data.get("admin_note", ""),
            "reviewed_by": admin_id,
            "reviewed_at": now,
            "updated_by": admin_id,
        }

        serializer = MentorTaskRequestReviewSerializer(
            data=data, instance=task_req, partial=True
        )
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        task_req = serializer.save()

        # On APPROVED — auto-create the TaskList entry
        if new_status == MentorTaskRequest.Status.APPROVED:
            task_type = TaskType.objects.first()  # default type — adjust as needed
            if not task_type:
                return CustomResponse(
                    general_message="No TaskType found. Cannot create task."
                ).get_failure_response()

            new_task = TaskList.objects.create(
                hashtag=task_req.hashtag,
                title=task_req.title,
                description=task_req.description,
                karma=task_req.karma,
                ig=task_req.ig,
                type=task_type,
                created_by_id=admin_id,
                updated_by_id=admin_id,
            )
            task_req.created_task = new_task
            task_req.save(update_fields=["created_task"])

        return CustomResponse(
            general_message=f"Task request {new_status.lower()}.",
            response={"task_request": MentorTaskRequestSerializer(task_req).data},
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# Opportunities
# ─────────────────────────────────────────────────────────────────────────────

class MentorOpportunityAPI(APIView):
    """GET — list; POST — create opportunity."""
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def get(self, request):
        ig_id = request.query_params.get("ig_id")
        opp_type = request.query_params.get("type")
        status_filter = request.query_params.get("status")

        qs = IgOpportunity.objects.select_related("ig", "created_by")
        if ig_id:
            qs = qs.filter(ig_id=ig_id)
        if opp_type:
            qs = qs.filter(type=opp_type)
        if status_filter:
            qs = qs.filter(status=status_filter)

        paginated = CommonUtils.get_paginated_queryset(
            qs, request,
            search_fields=["title", "ig__name"],
            sort_fields={
                "title": "title",
                "status": "status",
                "starts_at": "starts_at",
                "created_at": "created_at",
            },
        )
        serializer = IgOpportunitySerializer(paginated["queryset"], many=True)
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated["pagination"]
        )

    @role_required([ADMIN, MENTOR])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        ig_id = request.data.get("ig")
        if not ig_id or not InterestGroup.objects.filter(id=ig_id).exists():
            return CustomResponse(
                general_message="A valid 'ig' (Interest Group id) is required."
            ).get_failure_response()

        data = request.data.copy()
        data["created_by"] = user_id
        data["updated_by"] = user_id

        serializer = IgOpportunityWriteSerializer(data=data)
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        opp = serializer.save()

        _log_action(
            action_type=SystemActionLog.ActionType.OPPORTUNITY_POST,
            actor_user_id=user_id,
            entity_name="ig_opportunity",
            entity_id=opp.id,
            ig=opp.ig,
            new_data={"title": opp.title, "type": opp.type},
        )

        return CustomResponse(
            general_message="Opportunity created.",
            response={"opportunity": IgOpportunitySerializer(opp).data},
        ).get_success_response()


class MentorOpportunityDetailAPI(APIView):
    """GET / PUT / PATCH / DELETE a single opportunity."""
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def get(self, request, pk):
        opp = IgOpportunity.objects.select_related("ig", "created_by").filter(id=pk).first()
        if not opp:
            return CustomResponse(general_message="Opportunity not found.").get_failure_response()
        return CustomResponse(
            response={"opportunity": IgOpportunitySerializer(opp).data}
        ).get_success_response()

    @role_required([ADMIN, MENTOR])
    def patch(self, request, pk):
        user_id = JWTUtils.fetch_user_id(request)
        opp = IgOpportunity.objects.filter(id=pk).first()
        if not opp:
            return CustomResponse(general_message="Opportunity not found.").get_failure_response()

        data = request.data.copy()
        data["updated_by"] = user_id

        serializer = IgOpportunityWriteSerializer(data=data, instance=opp, partial=True)
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        serializer.save()

        _log_action(
            action_type=SystemActionLog.ActionType.IG_CONTENT_UPDATE,
            actor_user_id=user_id,
            entity_name="ig_opportunity",
            entity_id=opp.id,
            ig=opp.ig,
            new_data=request.data,
        )

        return CustomResponse(
            general_message="Opportunity updated.",
            response={"opportunity": IgOpportunitySerializer(opp).data},
        ).get_success_response()

    @role_required([ADMIN])
    def delete(self, request, pk):
        user_id = JWTUtils.fetch_user_id(request)
        opp = IgOpportunity.objects.filter(id=pk).first()
        if not opp:
            return CustomResponse(general_message="Opportunity not found.").get_failure_response()

        opp.status = IgOpportunity.Status.ARCHIVED
        opp.updated_by_id = user_id
        opp.save()
        return CustomResponse(
            general_message="Opportunity archived."
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# Mentees
# ─────────────────────────────────────────────────────────────────────────────

class MentorMenteesAPI(APIView):
    """GET — distinct mentees across sessions."""
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        is_admin = ADMIN in roles

        ig_id = request.query_params.get("ig_id")
        mentor_user_id = request.query_params.get("mentor_user_id")

        # Filter sessions
        session_qs = MentorshipSession.objects.all()
        if ig_id:
            session_qs = session_qs.filter(ig_id=ig_id)

        if not is_admin:
            # Mentor sees mentees from sessions they're a mentor/co-mentor in
            session_qs = session_qs.filter(
                participants__user_id=user_id,
                participants__participant_role__in=[
                    MentorshipSessionUserLink.ParticipantRole.MENTOR,
                    MentorshipSessionUserLink.ParticipantRole.CO_MENTOR,
                ],
            ).distinct()
        elif mentor_user_id:
            session_qs = session_qs.filter(
                participants__user_id=mentor_user_id,
                participants__participant_role__in=[
                    MentorshipSessionUserLink.ParticipantRole.MENTOR,
                    MentorshipSessionUserLink.ParticipantRole.CO_MENTOR,
                ],
            ).distinct()

        session_ids = session_qs.values_list("id", flat=True)

        mentees = (
            MentorshipSessionUserLink.objects
            .filter(
                session_id__in=session_ids,
                participant_role=MentorshipSessionUserLink.ParticipantRole.MENTEE,
            )
            .values(
                "user_id",
                "user__full_name",
                "user__muid",
                "user__email",
            )
            .annotate(
                total_sessions=Count("session_id"),
            )
            .order_by("-total_sessions")
        )

        paginated = CommonUtils.get_paginated_queryset(
            mentees, request,
            search_fields=["user__full_name", "user__muid"],
            sort_fields={
                "full_name": "user__full_name",
                "total_sessions": "total_sessions",
            },
        )

        return CustomResponse().paginated_response(
            data=list(paginated["queryset"]),
            pagination=paginated["pagination"],
        )


# ─────────────────────────────────────────────────────────────────────────────
# Activity Log
# ─────────────────────────────────────────────────────────────────────────────

class MentorActivityLogAPI(APIView):
    """GET — recent SystemActionLog entries."""
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        is_admin = ADMIN in roles

        ig_id = request.query_params.get("ig_id")
        action_type = request.query_params.get("action_type")

        log_qs = SystemActionLog.objects.select_related(
            "actor_user", "subject_user", "ig"
        ).order_by("-created_at")

        if not is_admin:
            log_qs = log_qs.filter(actor_user_id=user_id)
        if ig_id:
            log_qs = log_qs.filter(ig_id=ig_id)
        if action_type:
            log_qs = log_qs.filter(action_type=action_type)

        paginated = CommonUtils.get_paginated_queryset(
            log_qs, request,
            search_fields=["actor_user__full_name", "entity_name", "remarks"],
            sort_fields={"created_at": "created_at", "action_type": "action_type"},
        )
        serializer = SystemActionLogSerializer(paginated["queryset"], many=True)
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated["pagination"]
        )


# ─────────────────────────────────────────────────────────────────────────────
# Feature 1 — Karma Award (Admin awards karma to mentor after session)
# ─────────────────────────────────────────────────────────────────────────────

class MentorSessionKarmaAwardAPI(APIView):
    """
    GET  /mentor/sessions/<pk>/karma-award/ — list awards for this session
    POST /mentor/sessions/<pk>/karma-award/ — admin awards karma to a mentor
    """
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def get(self, request, pk):
        awards = (
            MentorKarmaAward.objects
            .filter(session_id=pk)
            .select_related("mentor", "awarded_by", "session")
        )
        serializer = MentorKarmaAwardSerializer(awards, many=True)
        return CustomResponse(
            response={"awards": serializer.data}
        ).get_success_response()

    @role_required([ADMIN])
    def post(self, request, pk):
        admin_id = JWTUtils.fetch_user_id(request)
        session = MentorshipSession.objects.filter(id=pk).select_related("ig").first()
        if not session:
            return CustomResponse(general_message="Session not found.").get_failure_response()

        if session.status != MentorshipSession.Status.COMPLETED:
            return CustomResponse(
                general_message="Karma can only be awarded for COMPLETED sessions."
            ).get_failure_response()

        serializer = MentorKarmaAwardWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        mentor_id = serializer.validated_data["mentor_id"]
        karma_pts = serializer.validated_data["karma"]
        note      = serializer.validated_data.get("note", "")

        # Mentor must be a MENTOR participant in the session
        is_participant = MentorshipSessionUserLink.objects.filter(
            session_id=pk,
            user_id=mentor_id,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
        ).exists()
        if not is_participant:
            return CustomResponse(
                general_message="User is not a MENTOR participant in this session."
            ).get_failure_response()

        # One award per (session, mentor)
        if MentorKarmaAward.objects.filter(session_id=pk, mentor_id=mentor_id).exists():
            return CustomResponse(
                general_message="Karma already awarded to this mentor for this session."
            ).get_failure_response()

        now = DateTimeUtils.get_current_utc_time()

        # Increment Wallet karma
        from db.task import Wallet
        wallet, _ = Wallet.objects.get_or_create(
            user_id=mentor_id,
            defaults={"created_by_id": admin_id, "updated_by_id": admin_id},
        )
        wallet.karma += karma_pts
        wallet.updated_by_id = admin_id
        wallet.save()

        # Create MentorKarmaAward
        award = MentorKarmaAward.objects.create(
            session_id=pk,
            mentor_id=mentor_id,
            karma=karma_pts,
            note=note,
            awarded_by_id=admin_id,
            awarded_at=now,
        )

        # Update mentor's total hours (1 karma award ≈ session duration)
        UserMentor.objects.filter(user_id=mentor_id).update(
            hours=models_F("hours") + 1
        )

        # Notify mentor
        Notification.objects.create(
            user_id=mentor_id,
            title="Karma Awarded 🎉",
            description=(
                f"You've been awarded {karma_pts} karma for session '{session.title}'."
            ),
            created_by_id=admin_id,
        )

        _log_action(
            action_type=SystemActionLog.ActionType.KARMA_AWARD,
            actor_user_id=admin_id,
            entity_name="mentor_karma_award",
            entity_id=award.id,
            subject_user=User.objects.filter(id=mentor_id).first(),
            ig=session.ig,
            new_data={"karma": karma_pts, "session_id": pk},
        )

        return CustomResponse(
            general_message=f"{karma_pts} karma awarded to mentor.",
            response={"award": MentorKarmaAwardSerializer(award).data},
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# Feature 2 — Mentee Task Review Queue
# ─────────────────────────────────────────────────────────────────────────────

class MentorTaskReviewQueueAPI(APIView):
    """
    GET  /mentor/review-queue/  — KAL entries pending mentor review in mentor's IGs
    """
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        is_admin = ADMIN in roles

        status_filter = request.query_params.get("status", "PENDING")
        ig_id = request.query_params.get("ig_id")

        kal_qs = (
            KarmaActivityLog.objects
            .select_related("user", "task__ig")
            .filter(mentor_review_status=status_filter)
        )

        if not is_admin:
            # Mentor sees only tasks from their IGs
            mentor_ig_ids = (
                MentorshipSessionUserLink.objects
                .filter(
                    user_id=user_id,
                    participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
                )
                .values_list("session__ig_id", flat=True)
                .distinct()
            )
            kal_qs = kal_qs.filter(task__ig_id__in=mentor_ig_ids)

        if ig_id:
            kal_qs = kal_qs.filter(task__ig_id=ig_id)

        paginated = CommonUtils.get_paginated_queryset(
            kal_qs, request,
            search_fields=["user__full_name", "task__title", "task__hashtag"],
            sort_fields={"created_at": "created_at", "karma": "karma"},
        )
        serializer = KarmaReviewQueueSerializer(paginated["queryset"], many=True)
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated["pagination"]
        )


class MentorTaskReviewDetailAPI(APIView):
    """
    PATCH /mentor/review-queue/<kal_id>/ — mentor approves or rejects a task submission
    Karma is NOT credited here; admin finalises via the existing appraiser flow.
    """
    authentication_classes = [CustomizePermission]

    @role_required([MENTOR])
    def patch(self, request, pk):
        mentor_id = JWTUtils.fetch_user_id(request)

        kal = KarmaActivityLog.objects.select_related(
            "user", "task__ig"
        ).filter(id=pk).first()
        if not kal:
            return CustomResponse(general_message="Task submission not found.").get_failure_response()

        if kal.mentor_review_status != "PENDING":
            return CustomResponse(
                general_message=f"Already reviewed: status is '{kal.mentor_review_status}'."
            ).get_failure_response()

        serializer = KarmaReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        now = DateTimeUtils.get_current_utc_time()
        new_status = serializer.validated_data["status"]
        feedback   = serializer.validated_data.get("feedback", "")

        kal.mentor_review_status   = new_status
        kal.mentor_reviewed_by_id  = mentor_id
        kal.mentor_reviewed_at     = now
        kal.mentor_review_feedback = feedback
        kal.updated_by_id          = mentor_id
        kal.save()

        _log_action(
            action_type=SystemActionLog.ActionType.TASK_REVIEW,
            actor_user_id=mentor_id,
            entity_name="karma_activity_log",
            entity_id=kal.id,
            subject_user=kal.user,
            ig=kal.task.ig if kal.task else None,
            new_data={"status": new_status, "feedback": feedback},
        )

        return CustomResponse(
            general_message=f"Task submission marked as {new_status}.",
            response={"status": new_status},
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# Feature 3 — Mentor Leaderboard
# ─────────────────────────────────────────────────────────────────────────────

class MentorLeaderboardAPI(APIView):
    """
    GET /mentor/leaderboard/
    Optional: ?ig_id=<id>

    Score = (sessions_completed × 3) + (mentees_attended × 2) + (hours × 1)
    """
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def get(self, request):
        ig_id = request.query_params.get("ig_id")

        # Base: only verified mentors
        mentor_qs = UserMentor.objects.filter(is_verified=True).select_related("user")

        # Sessions completed (scoped by IG if given)
        session_filter = Q(
            session_participations__session__status=MentorshipSession.Status.COMPLETED,
            session_participations__participant_role__in=[
                MentorshipSessionUserLink.ParticipantRole.MENTOR,
                MentorshipSessionUserLink.ParticipantRole.CO_MENTOR,
            ],
        )
        if ig_id:
            session_filter &= Q(session_participations__session__ig_id=ig_id)

        # Mentees attended
        mentee_filter = Q(
            session_participations__session__status=MentorshipSession.Status.COMPLETED,
            session_participations__participant_role__in=[
                MentorshipSessionUserLink.ParticipantRole.MENTOR,
                MentorshipSessionUserLink.ParticipantRole.CO_MENTOR,
            ],
        )

        rows = []
        for m in mentor_qs:
            sessions_completed = (
                MentorshipSessionUserLink.objects
                .filter(
                    user_id=m.user_id,
                    session__status=MentorshipSession.Status.COMPLETED,
                    participant_role__in=[
                        MentorshipSessionUserLink.ParticipantRole.MENTOR,
                        MentorshipSessionUserLink.ParticipantRole.CO_MENTOR,
                    ],
                    **({"session__ig_id": ig_id} if ig_id else {}),
                )
                .values("session_id").distinct().count()
            )

            session_ids = (
                MentorshipSessionUserLink.objects
                .filter(
                    user_id=m.user_id,
                    participant_role__in=[
                        MentorshipSessionUserLink.ParticipantRole.MENTOR,
                        MentorshipSessionUserLink.ParticipantRole.CO_MENTOR,
                    ],
                    **({"session__ig_id": ig_id} if ig_id else {}),
                )
                .values_list("session_id", flat=True)
            )
            mentees_attended = (
                MentorshipSessionUserLink.objects
                .filter(
                    session_id__in=session_ids,
                    participant_role=MentorshipSessionUserLink.ParticipantRole.MENTEE,
                    attendance_status=MentorshipSessionUserLink.AttendanceStatus.ATTENDED,
                )
                .count()
            )

            score = (sessions_completed * 3) + (mentees_attended * 2) + (m.hours * 1)
            rows.append({
                "mentor_id": m.user_id,
                "full_name": m.user.full_name,
                "muid": m.user.muid,
                "profile_pic": m.user.profile_pic,
                "mentor_tier": m.mentor_tier,
                "sessions_completed": sessions_completed,
                "mentees_attended": mentees_attended,
                "hours": m.hours,
                "score": score,
            })

        rows.sort(key=lambda x: x["score"], reverse=True)
        for i, row in enumerate(rows, start=1):
            row["rank"] = i

        # Paginate manually
        page = int(request.query_params.get("pageIndex", 1))
        per_page = int(request.query_params.get("perPage", 10))
        total = len(rows)
        start = (page - 1) * per_page
        page_rows = rows[start: start + per_page]

        serializer = MentorLeaderboardSerializer(page_rows, many=True)
        import math
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination={
                "count": total,
                "totalPages": math.ceil(total / per_page) if per_page else 1,
                "isNext": (page * per_page) < total,
                "isPrev": page > 1,
                "nextPage": page + 1 if (page * per_page) < total else None,
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# Feature 4 — Session Reminder Notifications
# ─────────────────────────────────────────────────────────────────────────────

class MentorSessionRemindAPI(APIView):
    """
    POST /mentor/sessions/<pk>/remind/
    Sends a Notification to every participant (INVITED or ATTENDED) in the session.
    Also called automatically on session creation/status→SCHEDULED (see helper below).
    """
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def post(self, request, pk):
        user_id = JWTUtils.fetch_user_id(request)
        session = MentorshipSession.objects.filter(id=pk).first()
        if not session:
            return CustomResponse(general_message="Session not found.").get_failure_response()

        if session.status not in [
            MentorshipSession.Status.SCHEDULED,
            MentorshipSession.Status.PENDING_APPROVAL,
        ]:
            return CustomResponse(
                general_message="Reminders can only be sent for SCHEDULED or PENDING_APPROVAL sessions."
            ).get_failure_response()

        count = _send_session_reminders(session, triggered_by_id=user_id)
        return CustomResponse(
            general_message=f"Reminder sent to {count} participant(s)."
        ).get_success_response()


def _send_session_reminders(session, triggered_by_id):
    """
    Creates Notification rows for all INVITED/ATTENDED participants.
    Returns the count of notifications created.
    """
    participants = MentorshipSessionUserLink.objects.filter(
        session_id=session.id,
        attendance_status__in=[
            MentorshipSessionUserLink.AttendanceStatus.INVITED,
            MentorshipSessionUserLink.AttendanceStatus.ATTENDED,
        ],
    ).values_list("user_id", flat=True)

    starts_str = session.starts_at.strftime("%d %b %Y at %H:%M UTC")
    notifications = [
        Notification(
            user_id=uid,
            title="📅 Session Reminder",
            description=f"'{session.title}' starts on {starts_str}. Don't miss it!",
            url=f"/sessions/{session.id}/",
            created_by_id=triggered_by_id,
        )
        for uid in participants
    ]
    Notification.objects.bulk_create(notifications, ignore_conflicts=True)
    return len(notifications)


# ─────────────────────────────────────────────────────────────────────────────
# My IGs — mentor sees their own active IG links
# ─────────────────────────────────────────────────────────────────────────────

class MentorMyIgsAPI(APIView):
    """
    GET /mentor/my-igs/
    Returns all IGs the authenticated mentor is actively linked to
    (UserIgLink with assignment_type=MENTOR, is_active=True).
    """
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        links = UserIgLink.objects.filter(
            user_id=user_id,
            assignment_type=UserIgLink.AssignmentType.MENTOR,
            is_active=True,
        ).select_related("ig")

        data = [
            {
                "ig_id":    str(link.ig_id),
                "ig_name":  link.ig.name,
                "ig_code":  link.ig.code,
            }
            for link in links
        ]
        return CustomResponse(response={"igs": data}).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# IG Mentor Link Requests — IG Lead reviews pending requests
# ─────────────────────────────────────────────────────────────────────────────

class MentorIgRequestListAPI(APIView):
    """
    GET /mentor/ig-requests/?ig_id=<uuid>
    IG Lead (or Admin) views pending mentor-to-IG link requests for their IG.
    Pending = UserIgLink(assignment_type=MENTOR, is_active=False).
    """
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def get(self, request):
        user_id  = JWTUtils.fetch_user_id(request)
        roles    = JWTUtils.fetch_role(request)
        is_admin = ADMIN in roles
        ig_id    = request.query_params.get("ig_id")

        if not ig_id:
            return CustomResponse(
                general_message="ig_id query param is required."
            ).get_failure_response()

        ig = InterestGroup.objects.filter(id=ig_id).first()
        if not ig:
            return CustomResponse(general_message="Interest Group not found.").get_failure_response()

        # Permission: admin OR IG Lead for this specific IG
        ig_lead_role = RoleType.IG_LEAD_ROLE(ig.code)
        if not is_admin and ig_lead_role not in roles:
            return CustomResponse(
                general_message="You are not an IG Lead for this interest group."
            ).get_failure_response()

        pending = UserIgLink.objects.filter(
            ig_id=ig_id,
            assignment_type=UserIgLink.AssignmentType.MENTOR,
            is_active=False,
        ).select_related("user", "ig")

        data = [
            {
                "id":           str(link.id),
                "user_id":      str(link.user_id),
                "full_name":    link.user.full_name,
                "email":        link.user.email,
                "muid":         link.user.muid,
                "ig_id":        str(link.ig_id),
                "ig_name":      link.ig.name,
                "requested_at": link.created_at,
            }
            for link in pending
        ]
        return CustomResponse(response={"requests": data}).get_success_response()


class MentorIgRequestDetailAPI(APIView):
    """
    PATCH /mentor/ig-requests/<uil_pk>/
    IG Lead approves or rejects a pending mentor IG link request.

    Body:
        action : "approve" | "reject"
        note   : str (optional, shown to mentor on reject)

    Approve → UserIgLink.is_active = True, mentor notified
    Reject  → UserIgLink row deleted, mentor notified
    """
    authentication_classes = [CustomizePermission]

    @role_required([ADMIN, MENTOR])
    def patch(self, request, pk):
        user_id  = JWTUtils.fetch_user_id(request)
        roles    = JWTUtils.fetch_role(request)
        is_admin = ADMIN in roles

        link = UserIgLink.objects.filter(
            id=pk,
            assignment_type=UserIgLink.AssignmentType.MENTOR,
            is_active=False,
        ).select_related("user", "ig").first()

        if not link:
            return CustomResponse(
                general_message="Pending request not found."
            ).get_failure_response()

        # Permission: admin OR IG Lead for this IG
        ig_lead_role = RoleType.IG_LEAD_ROLE(link.ig.code)
        if not is_admin and ig_lead_role not in roles:
            return CustomResponse(
                general_message="You are not an IG Lead for this interest group."
            ).get_failure_response()

        action = request.data.get("action", "").lower()
        note   = request.data.get("note", "")

        if action not in ("approve", "reject"):
            return CustomResponse(
                general_message="'action' must be 'approve' or 'reject'."
            ).get_failure_response()

        mentor_user = link.user
        ig_name     = link.ig.name

        if action == "approve":
            link.is_active     = True
            link.assigned_by_id = user_id
            link.save()

            Notification.objects.create(
                user=mentor_user,
                title=f"✅ IG Mentor Request Approved — {ig_name}",
                description=(
                    f"Your request to be linked as a mentor for {ig_name} "
                    f"has been approved. You can now create sessions for this IG."
                ),
                created_by_id=user_id,
            )
            return CustomResponse(
                general_message=f"Mentor approved for {ig_name}."
            ).get_success_response()

        # reject
        link.delete()
        Notification.objects.create(
            user=mentor_user,
            title=f"❌ IG Mentor Request Not Approved — {ig_name}",
            description=(
                f"Your request to be linked as a mentor for {ig_name} was not approved."
                + (f" Reason: {note}" if note else "")
            ),
            created_by_id=user_id,
        )
        return CustomResponse(
            general_message=f"Mentor request for {ig_name} rejected."
        ).get_success_response()

