from rest_framework.views import APIView

from db.user import User, UserMentor
from db.mentor import MentorshipSession, MentorshipSessionUserLink
from utils.permission import CustomizePermission, JWTUtils
from utils.mentor_permissions import IsIGMentor, _get_persona_context
from utils.response import CustomResponse
from utils.utils import CommonUtils
from .serializers import (
    MentorSessionCreateSerializer,
    MentorSessionListSerializer,
    MentorSessionUpdateSerializer,
)


class MentorSessionView(APIView):
    """
    GET  /api/v1/dashboard/mentor/sessions/
        Returns a paginated list of sessions the current user is a MENTOR in,
        scoped to the active persona IG.

    POST /api/v1/dashboard/mentor/sessions/
        Creates a new session. Requires verified mentor status.
        ig_id is derived from the active persona context — NOT accepted from the body.
    """
    permission_classes = [CustomizePermission, IsIGMentor]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        persona_ctx = _get_persona_context(request)
        active_ig_id = persona_ctx['ig_id']

        mentor_session_ids = MentorshipSessionUserLink.objects.filter(
            user_id=user_id,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
        ).values_list("session_id", flat=True)

        sessions = (
            MentorshipSession.objects
            .filter(id__in=mentor_session_ids, ig_id=active_ig_id)
            .select_related("ig")
            .prefetch_related("participants__user")
        )

        params = request.query_params
        if status_val := params.get("status"):
            sessions = sessions.filter(status=status_val)
        if mode := params.get("mode"):
            sessions = sessions.filter(mode=mode)
        if date_from := params.get("date_from"):
            sessions = sessions.filter(starts_at__date__gte=date_from)
        if date_to := params.get("date_to"):
            sessions = sessions.filter(starts_at__date__lte=date_to)

        paginated = CommonUtils.get_paginated_queryset(
            sessions,
            request,
            search_fields=["title"],
            sort_fields={"starts_at": "starts_at", "title": "title"},
        )

        serializer = MentorSessionListSerializer(paginated["queryset"], many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated["pagination"],
            }
        ).get_success_response()

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        persona_ctx = _get_persona_context(request)

        # Verified mentor check — only verified mentors can create sessions
        mentor = UserMentor.objects.filter(user_id=user_id).first()
        if mentor is None or not mentor.is_verified:
            return CustomResponse(
                general_message="Only verified mentors can create sessions"
            ).get_failure_response()

        active_ig_id = persona_ctx['ig_id']

        serializer = MentorSessionCreateSerializer(
            data=request.data,
            context={"user_id": user_id, "ig_id": active_ig_id},
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Session created successfully"
            ).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()


class MentorSessionDetailView(APIView):
    """
    PATCH /api/v1/dashboard/mentor/sessions/<session_id>/
        Updates session status and/or participant attendance/notes.
        Only the mentor who owns the session can patch it.
    """
    permission_classes = [CustomizePermission, IsIGMentor]

    def patch(self, request, session_id):
        user_id = JWTUtils.fetch_user_id(request)

        session = MentorshipSession.objects.filter(id=session_id).first()
        if session is None:
            return CustomResponse(
                general_message="Session not found"
            ).get_failure_response()

        # Ownership check — only the mentor who ran the session can update it
        is_mentor_participant = MentorshipSessionUserLink.objects.filter(
            session=session,
            user_id=user_id,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
        ).exists()
        if not is_mentor_participant:
            return CustomResponse(
                general_message="You are not a mentor participant in this session"
            ).get_failure_response()

        serializer = MentorSessionUpdateSerializer(
            data=request.data,
            partial=True,
            context={"user_id": user_id},
        )
        if serializer.is_valid():
            serializer.update(session, serializer.validated_data)
            return CustomResponse(
                general_message="Session updated successfully"
            ).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()
