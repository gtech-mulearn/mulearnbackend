from rest_framework.views import APIView
from django.db.models import Sum, Avg, Count
from drf_spectacular.utils import extend_schema

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from db.user import UserMentor, MentorApplication, Socials
from db.mentor import MentorshipSession, MentorshipSessionUserLink, MentorKarmaAward


class MentorPersonalAnalyticsAPI(APIView):
    """
    A mentor's own activity — session history, karma earned, hours
    contributed, ratings/feedback. Distinct from `get_mentor_overview`
    (scope-level metrics, e.g. total learners in their IG/campus/company)
    and from `MentorActivityListAPI` (a raw activity feed, no aggregates).
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="The caller's own session history, karma earned, hours contributed, and ratings/feedback.",
    )
    @role_required([RoleType.MENTOR.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        sessions = MentorshipSession.objects.filter(created_by_id=user_id, is_deleted=False)
        session_counts = {
            "total": sessions.count(),
            "completed": sessions.filter(status=MentorshipSession.Status.COMPLETED).count(),
            "upcoming": sessions.filter(status=MentorshipSession.Status.SCHEDULED).count(),
            "cancelled": sessions.filter(status=MentorshipSession.Status.CANCELLED).count(),
        }

        karma_earned = MentorKarmaAward.objects.filter(mentor_id=user_id).aggregate(
            total=Sum('karma')
        )['total'] or 0

        contributed_minutes = MentorshipSessionUserLink.objects.filter(
            user_id=user_id,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
        ).aggregate(total=Sum('contributed_minutes'))['total'] or 0

        rating_aggregate = MentorshipSessionUserLink.objects.filter(
            user_id=user_id,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
            rating__isnull=False,
        ).aggregate(average=Avg('rating'), count=Count('id'))

        mentor_profile = UserMentor.objects.filter(user_id=user_id).first()

        recent_feedback_links = (
            MentorshipSessionUserLink.objects.filter(
                user_id=user_id,
                participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
            )
            .exclude(feedback__isnull=True)
            .exclude(feedback__exact='')
            .select_related('session')
            .order_by('-created_at')[:10]
        )
        recent_feedback = [
            {
                "session_id": link.session_id,
                "session_title": link.session.title if link.session else None,
                "rating": link.rating,
                "feedback": link.feedback,
                "date": link.created_at,
            }
            for link in recent_feedback_links
        ]

        return CustomResponse(response={
            "sessions": session_counts,
            "karma_earned": karma_earned,
            "hours_contributed": round(contributed_minutes / 60, 2),
            "profile_hours": mentor_profile.hours if mentor_profile else 0,
            "rating": {
                "average": rating_aggregate["average"],
                "count": rating_aggregate["count"] or 0,
            },
            "recent_feedback": recent_feedback,
        }).get_success_response()


class MentorProfileCompletionAPI(APIView):
    """
    Weighted checklist of how complete a mentor's profile is — surfaced so
    the mentor knows what to fill in to look credible to learners/companies.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="The caller's mentor-profile completion percentage and a field-by-field checklist.",
    )
    @role_required([RoleType.MENTOR.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        mentor_profile = UserMentor.objects.filter(user_id=user_id).first()
        socials = Socials.objects.filter(user_id=user_id).first()

        checklist = {
            "about": bool(mentor_profile and mentor_profile.about),
            "expertise": bool(mentor_profile and mentor_profile.expertise),
            "hours": bool(mentor_profile and mentor_profile.hours),
            "linkedin": bool(socials and socials.linkedin),
        }

        ig_mentor_app = MentorApplication.objects.filter(
            user_id=user_id,
            mentor_tier=MentorApplication.MentorTier.IG_MENTOR,
            status=MentorApplication.Status.APPROVED,
        ).first()

        if ig_mentor_app:
            checklist["preferred_igs"] = bool(ig_mentor_app.preferred_ig_ids)
        else:
            # Not an IG mentor, so this check is not applicable
            checklist["preferred_igs"] = None

        applicable = [v for v in checklist.values() if v is not None]
        completed = sum(1 for v in applicable if v)
        percentage = round((completed / len(applicable)) * 100) if applicable else 0

        return CustomResponse(response={
            "percentage": percentage,
            "checklist": checklist,
        }).get_success_response()
