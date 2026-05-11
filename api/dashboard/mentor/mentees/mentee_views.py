from django.db.models import Count, Max, F

from rest_framework.views import APIView

from db.user import User
from db.task import UserIgLvlLink
from db.mentor import MentorshipSession, MentorshipSessionUserLink
from db.achievement import UserIgKarma
from utils.permission import CustomizePermission, JWTUtils
from utils.mentor_permissions import IsIGMentor, _get_persona_context
from utils.response import CustomResponse
from utils.utils import CommonUtils


class MentorMenteeView(APIView):
    """
    GET /api/v1/dashboard/mentor/mentees/

    Returns a paginated list of mentees the current mentor has sessions with,
    enriched with karma, level, and session progress data.

    Scoped to the active persona IG by default.
    Accepts an optional `ig_id` query param to override (must still be a valid
    IG for this mentor's sessions).
    """
    permission_classes = [CustomizePermission, IsIGMentor]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        persona_ctx = _get_persona_context(request)

        # Default to active persona IG; allow optional override via query param
        ig_id = request.query_params.get("ig_id") or persona_ctx['ig_id']

        # All sessions this mentor is a MENTOR participant in
        mentor_session_ids = MentorshipSessionUserLink.objects.filter(
            user_id=user_id,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
        ).values_list("session_id", flat=True)

        # Filter by IG
        session_ids_in_ig = MentorshipSession.objects.filter(
            id__in=mentor_session_ids, ig_id=ig_id
        ).values_list("id", flat=True)

        # Get mentee links in those sessions
        mentee_links = MentorshipSessionUserLink.objects.filter(
            session_id__in=session_ids_in_ig,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTEE,
        )

        # Aggregate per mentee
        mentee_stats = (
            mentee_links
            .values("user_id")
            .annotate(
                session_count=Count("id"),
                last_session_at=Max("session__starts_at"),
            )
        )

        mentee_ids = [m["user_id"] for m in mentee_stats]
        stats_map = {m["user_id"]: m for m in mentee_stats}

        mentees = (
            User.objects.filter(id__in=mentee_ids)
            .annotate(
                karma=F("wallet_user__karma"),
                level=F("user_lvl_link_user__level__name"),
            )
        )

        paginated = CommonUtils.get_paginated_queryset(
            mentees,
            request,
            search_fields=["full_name", "muid"],
            sort_fields={
                "full_name": "full_name",
                "karma": "wallet_user__karma",
            },
        )

        data = []
        for mentee in paginated["queryset"]:
            stats = stats_map.get(mentee.id, {})

            # IG-specific karma and level
            ig_karma = None
            ig_karma_obj = UserIgKarma.objects.filter(
                user_id=mentee.id, ig_id=ig_id
            ).first()
            if ig_karma_obj:
                ig_karma = ig_karma_obj.total_karma

            ig_level = None
            ig_lvl_obj = UserIgLvlLink.objects.filter(
                user_id=mentee.id, ig_id=ig_id
            ).select_related("level").first()
            if ig_lvl_obj:
                ig_level = ig_lvl_obj.level.name

            data.append({
                "user_id": mentee.id,
                "full_name": mentee.full_name,
                "muid": mentee.muid,
                "profile_pic": str(mentee.profile_pic) if mentee.profile_pic else None,
                "karma": mentee.karma or 0,
                "level": mentee.level,
                "ig_karma": ig_karma,
                "ig_level": ig_level,
                "session_count": stats.get("session_count", 0),
                "last_session_at": stats.get("last_session_at"),
            })

        return CustomResponse(
            response={
                "active_ig_id": ig_id,
                "data": data,
                "pagination": paginated["pagination"],
            }
        ).get_success_response()
