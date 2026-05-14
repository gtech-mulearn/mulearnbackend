from rest_framework.views import APIView

from db.user import User, UserRoleLink, UserMentor, UserSettings
from django.db.models import Count, Sum
from django.utils import timezone

from db.task import InterestGroup, KarmaActivityLog, UserIgLvlLink
from db.mentor import MentorshipSession, MentorshipSessionUserLink
from db.achievement import UserIgKarma
from utils.permission import CustomizePermission, JWTUtils
from utils.mentor_permissions import IsIGMentor, _get_persona_context
from utils.response import CustomResponse


class MentorOverviewView(APIView):
    """
    GET /api/v1/dashboard/mentor/overview/

    Returns a full dashboard snapshot for the active mentor persona:
    - User details
    - Mentor profile (with tier + verification)
    - Active persona context (IG, role_link)
    - All authorized IGs (not just the active one)
    - Key stats (mentees, sessions, pending approvals, hours)
    """
    permission_classes = [CustomizePermission, IsIGMentor]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        # persona_context already validated and cached by IsIGMentor
        persona_ctx = _get_persona_context(request)

        user = User.objects.filter(id=user_id).first()
        mentor_profile = UserMentor.objects.filter(user_id=user_id).first()

        # All active IG-scoped mentor role links for this user
        ig_role_links = (
            UserRoleLink.objects
            .select_related('ig')
            .filter(user_id=user_id, role__title='Mentor', ig__isnull=False, is_active=True)
        )

        authorized_igs = [
            {
                "role_link_id": str(rl.id),
                "ig_id": str(rl.ig.id),
                "ig_name": rl.ig.name,
                "is_primary": rl.is_primary,
                "is_verified": mentor_profile.is_verified if mentor_profile else False,
            }
            for rl in ig_role_links
        ]

        active_ig_id = persona_ctx['ig_id']

        # Stats scoped to current active IG — only sessions this mentor ran
        mentor_session_ids = (
            MentorshipSessionUserLink.objects
            .filter(
                user_id=user_id,
                participant_role='MENTOR',
                session__ig_id=active_ig_id,
            )
            .values_list('session_id', flat=True)
        )

        total_mentees = (
            MentorshipSessionUserLink.objects
            .filter(
                session_id__in=mentor_session_ids,
                participant_role='MENTEE',
            )
            .values('user_id').distinct().count()
        )

        sessions_conducted = (
            MentorshipSessionUserLink.objects
            .filter(
                user_id=user_id,
                participant_role='MENTOR',
                session__ig_id=active_ig_id,
                session__status='COMPLETED',
            )
            .count()
        )

        pending_approvals = KarmaActivityLog.objects.filter(
            task__ig_id=active_ig_id,
            mentor_review_status='PENDING',
        ).count()

        return CustomResponse(
            general_message="Mentor overview fetched.",
            response={
                "user": {
                    "full_name": user.full_name,
                    "muid": user.muid,
                    "profile_pic": user.profile_pic,
                },
                "mentor_profile": {
                    "about": mentor_profile.about if mentor_profile else None,
                    "expertise": mentor_profile.expertise if mentor_profile else None,
                    "reason": mentor_profile.reason if mentor_profile else None,
                    "volunteer_hours": mentor_profile.hours if mentor_profile else 0,
                    "mentor_tier": mentor_profile.mentor_tier if mentor_profile else "NORMAL",
                    "is_verified": mentor_profile.is_verified if mentor_profile else False,
                },
                "active_persona": {
                    "active_persona": "mentor",
                    "active_role_link_id": persona_ctx['role_link_id'],
                    "active_ig_id": active_ig_id,
                    "ig_name": persona_ctx['role_link'].ig.name if persona_ctx['role_link'].ig else None,
                    "is_verified": mentor_profile.is_verified if mentor_profile else False,
                },
                "authorized_igs": authorized_igs,
                "stats": {
                    "total_mentees": total_mentees,
                    "sessions_conducted": sessions_conducted,
                    "pending_task_approvals": pending_approvals,
                    "volunteer_hours": mentor_profile.hours if mentor_profile else 0,
                },
            }
        ).get_success_response()


class MentorHomeSummaryView(APIView):
    permission_classes = [CustomizePermission, IsIGMentor]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        persona_ctx = _get_persona_context(request)
        active_ig_id = request.query_params.get("ig_id") or persona_ctx["ig_id"]
        mentor_profile = UserMentor.objects.filter(user_id=user_id).first()

        mentor_session_ids = MentorshipSessionUserLink.objects.filter(
            user_id=user_id,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
            session__ig_id=active_ig_id,
        ).values_list("session_id", flat=True)

        sessions = MentorshipSession.objects.filter(
            id__in=mentor_session_ids,
            ig_id=active_ig_id,
        ).prefetch_related("participants__user")

        completed_sessions = sessions.filter(status=MentorshipSession.Status.COMPLETED)
        total_sessions = sessions.count()
        completed_count = completed_sessions.count()
        total_minutes = (
            MentorshipSessionUserLink.objects.filter(
                user_id=user_id,
                participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
                session_id__in=mentor_session_ids,
            ).aggregate(total=Sum("contributed_minutes")).get("total")
            or 0
        )
        mentee_links = MentorshipSessionUserLink.objects.filter(
            session_id__in=mentor_session_ids,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTEE,
        ).select_related("user")
        active_mentees = mentee_links.values("user_id").distinct().count()

        next_session = sessions.filter(
            starts_at__gte=timezone.now(),
            status=MentorshipSession.Status.SCHEDULED,
        ).order_by("starts_at").first()

        def _mentee_for_session(session):
            if not session:
                return None
            return next(
                (p.user for p in session.participants.all() if p.participant_role == MentorshipSessionUserLink.ParticipantRole.MENTEE),
                None,
            )

        next_mentee = _mentee_for_session(next_session)
        upcoming_sessions = []
        for session in sessions.filter(
            starts_at__gte=timezone.now(),
            status=MentorshipSession.Status.SCHEDULED,
        ).order_by("starts_at")[:5]:
            mentee = _mentee_for_session(session)
            upcoming_sessions.append({
                "id": str(session.id),
                "title": session.title,
                "mentee": {
                    "id": str(mentee.id),
                    "full_name": mentee.full_name,
                    "muid": mentee.muid,
                    "profile_pic": mentee.profile_pic,
                } if mentee else None,
                "topic": session.description,
                "starts_at": session.starts_at.isoformat(),
                "ends_at": session.ends_at.isoformat(),
                "mode": session.mode,
                "status": session.status,
            })

        mentee_progress = []
        seen = set()
        for link in mentee_links:
            if link.user_id in seen:
                continue
            seen.add(link.user_id)
            ig_karma = UserIgKarma.objects.filter(user_id=link.user_id, ig_id=active_ig_id).first()
            ig_level = UserIgLvlLink.objects.filter(user_id=link.user_id, ig_id=active_ig_id).select_related("level").first()
            session_count = mentee_links.filter(user_id=link.user_id).count()
            mentee_progress.append({
                "user_id": str(link.user.id),
                "full_name": link.user.full_name,
                "muid": link.user.muid,
                "profile_pic": link.user.profile_pic,
                "ig_karma": ig_karma.total_karma if ig_karma else 0,
                "target_karma": 1000,
                "progress_percent": min(round(((ig_karma.total_karma if ig_karma else 0) / 1000) * 100, 2), 100),
                "ig_level": ig_level.level.name if ig_level else None,
                "session_count": session_count,
                "last_session_at": link.session.starts_at.isoformat() if link.session else None,
            })

        expertise = mentor_profile.expertise if mentor_profile else None
        if isinstance(expertise, str):
            expertise = [item.strip() for item in expertise.split(",") if item.strip()]

        return CustomResponse(
            general_message="Mentor dashboard summary fetched successfully",
            response={
                "next_session": {
                    "id": str(next_session.id),
                    "title": next_session.title,
                    "mentee_name": next_mentee.full_name if next_mentee else None,
                    "mentee_muid": next_mentee.muid if next_mentee else None,
                    "starts_at": next_session.starts_at.isoformat(),
                    "mode": next_session.mode,
                    "meeting_link": next_session.meeting_link,
                } if next_session else None,
                "stat_cards": [
                    {"key": "active_mentees", "label": "Active mentees", "value": active_mentees, "delta": 0, "delta_type": "neutral", "period": "30d"},
                    {"key": "hours_mentored", "label": "Hours mentored", "value": round(total_minutes / 60, 2) or (mentor_profile.hours if mentor_profile else 0), "delta": 0, "delta_type": "neutral", "period": "30d"},
                    {"key": "avg_rating", "label": "Avg rating", "value": None, "delta": 0, "delta_type": "neutral", "period": "30d"},
                    {"key": "completion_rate", "label": "Completion rate", "value": round((completed_count / total_sessions) * 100, 2) if total_sessions else 0, "unit": "percent", "delta": 0, "delta_type": "neutral", "period": "30d"},
                ],
                "upcoming_sessions": upcoming_sessions,
                "session_requests": [],
                "mentee_progress": mentee_progress,
                "expertise_tags": expertise or [],
            },
        ).get_success_response()
