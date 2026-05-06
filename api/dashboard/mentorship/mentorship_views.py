from django.db.models import Count, Max, F
from django.utils import timezone
from rest_framework.views import APIView

from db.user import User, UserMentor
from db.task import (
    KarmaActivityLog, UserIgLink, UserIgLvlLink,
    MentorshipSession, MentorshipSessionUserLink,
)
from db.achievement import UserIgKarma
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from . import serializers as mentorship_serializers


class MentorStatusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.MENTOR.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        mentor = UserMentor.objects.filter(user_id=user_id).first()
        if mentor is None:
            return CustomResponse(
                general_message="Mentor profile not found"
            ).get_failure_response()

        serializer = mentorship_serializers.MentorStatusSerializer(mentor)
        return CustomResponse(response=serializer.data).get_success_response()


class MentorProfileAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.MENTOR.value])
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        mentor = UserMentor.objects.filter(user_id=user_id).first()
        if mentor is None:
            return CustomResponse(
                general_message="Mentor profile not found"
            ).get_failure_response()

        serializer = mentorship_serializers.MentorProfileUpdateSerializer(
            mentor, data=request.data, partial=True,
            context={"user_id": user_id},
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Profile updated successfully"
            ).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()


class MentorSessionAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.MENTOR.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        mentor_session_ids = MentorshipSessionUserLink.objects.filter(
            user_id=user_id,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
        ).values_list("session_id", flat=True)

        sessions = MentorshipSession.objects.filter(
            id__in=mentor_session_ids
        ).select_related("ig").prefetch_related("session_user_links__user")

        params = request.query_params

        if status := params.get("status"):
            sessions = sessions.filter(status=status)

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
            sort_fields={
                "starts_at": "starts_at",
                "title": "title",
            },
        )

        serializer = mentorship_serializers.MentorSessionListSerializer(
            paginated["queryset"], many=True
        )
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated["pagination"],
            }
        ).get_success_response()

    @role_required([RoleType.MENTOR.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        mentor = UserMentor.objects.filter(user_id=user_id).first()
        if mentor is None or not mentor.is_verified:
            return CustomResponse(
                general_message="Only verified mentors can create sessions"
            ).get_failure_response(
                status_code=403,
                http_status_code=403,
            )

        ig_id = request.data.get("ig_id")
        if ig_id:
            is_mentor_for_ig = UserIgLink.objects.filter(
                user_id=user_id,
                ig_id=ig_id,
                assignment_type='MENTOR',
                is_active=True,
            ).exists()
            if not is_mentor_for_ig:
                return CustomResponse(
                    general_message="You are not authorized for this interest group"
                ).get_failure_response(
                    status_code=403,
                    http_status_code=403,
                )

        serializer = mentorship_serializers.MentorSessionCreateSerializer(
            data=request.data, context={"user_id": user_id}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Session created successfully"
            ).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.MENTOR.value])
    def patch(self, request, session_id=None):
        if not session_id:
            return CustomResponse(
                general_message="session_id is required"
            ).get_failure_response()

        user_id = JWTUtils.fetch_user_id(request)

        session = MentorshipSession.objects.filter(id=session_id).first()
        if session is None:
            return CustomResponse(
                general_message="Session not found"
            ).get_failure_response()

        is_mentor_participant = MentorshipSessionUserLink.objects.filter(
            session=session,
            user_id=user_id,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
        ).exists()
        if not is_mentor_participant:
            return CustomResponse(
                general_message="Not a mentor participant in this session"
            ).get_failure_response(
                status_code=403,
                http_status_code=403,
            )

        serializer = mentorship_serializers.MentorSessionUpdateSerializer(
            data=request.data, partial=True,
            context={"user_id": user_id},
        )
        if serializer.is_valid():
            serializer.update(session, serializer.validated_data)
            return CustomResponse(
                general_message="Session updated successfully"
            ).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()


class MentorMenteeAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.MENTOR.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        ig_id = request.query_params.get("ig_id")

        mentor_session_ids = MentorshipSessionUserLink.objects.filter(
            user_id=user_id,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
        ).values_list("session_id", flat=True)

        mentee_links = MentorshipSessionUserLink.objects.filter(
            session_id__in=mentor_session_ids,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTEE,
        )

        if ig_id:
            session_ids_in_ig = MentorshipSession.objects.filter(
                id__in=mentor_session_ids, ig_id=ig_id
            ).values_list("id", flat=True)
            mentee_links = mentee_links.filter(session_id__in=session_ids_in_ig)

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

            ig_karma = None
            ig_level = None
            if ig_id:
                ig_karma_obj = UserIgKarma.objects.filter(
                    user_id=mentee.id, ig_id=ig_id
                ).first()
                if ig_karma_obj:
                    ig_karma = ig_karma_obj.total_karma

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
                "data": data,
                "pagination": paginated["pagination"],
            }
        ).get_success_response()


class MentorTaskQueueAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.MENTOR.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        mentor = UserMentor.objects.filter(user_id=user_id).first()
        if mentor is None or not mentor.is_verified:
            return CustomResponse(
                general_message="Only verified mentors can access the task queue"
            ).get_failure_response(
                status_code=403,
                http_status_code=403,
            )

        mentor_ig_ids = list(
            UserIgLink.objects.filter(
                user_id=user_id,
                assignment_type='MENTOR',
                is_active=True,
            ).values_list("ig_id", flat=True)
        )

        logs = (
            KarmaActivityLog.objects.filter(
                task__ig_id__in=mentor_ig_ids
            )
            .select_related("user", "task", "task__ig")
        )

        params = request.query_params
        if ig_id := params.get("ig_id"):
            logs = logs.filter(task__ig_id=ig_id)

        allowed_statuses = {"PENDING", "APPROVED", "REJECTED"}
        status_filter = params.get("status", "PENDING").upper()
        if status_filter not in allowed_statuses:
            return CustomResponse(
                general_message="Invalid status filter. Must be PENDING, APPROVED, or REJECTED"
            ).get_failure_response()
        logs = logs.filter(mentor_review_status=status_filter)

        logs = logs.order_by("-created_at")

        paginated = CommonUtils.get_paginated_queryset(
            logs,
            request,
            search_fields=["user__full_name", "task__title"],
            sort_fields={
                "created_at": "created_at",
            },
        )

        serializer = mentorship_serializers.TaskQueueSerializer(
            paginated["queryset"], many=True
        )
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated["pagination"],
            }
        ).get_success_response()

    @role_required([RoleType.MENTOR.value])
    def patch(self, request, log_id=None):
        if not log_id:
            return CustomResponse(
                general_message="log_id is required"
            ).get_failure_response()

        user_id = JWTUtils.fetch_user_id(request)

        mentor = UserMentor.objects.filter(user_id=user_id).first()
        if mentor is None or not mentor.is_verified:
            return CustomResponse(
                general_message="Only verified mentors can approve tasks"
            ).get_failure_response(
                status_code=403,
                http_status_code=403,
            )

        log_entry = KarmaActivityLog.objects.filter(
            id=log_id
        ).select_related("task", "task__ig").first()

        if log_entry is None:
            return CustomResponse(
                general_message="Karma log entry not found"
            ).get_failure_response()

        if log_entry.mentor_review_status != "PENDING":
            return CustomResponse(
                general_message="This task has already been actioned"
            ).get_failure_response(
                status_code=403,
                http_status_code=403,
            )

        if log_entry.task and log_entry.task.ig:
            is_authorized = UserIgLink.objects.filter(
                user_id=user_id,
                ig_id=log_entry.task.ig_id,
                assignment_type='MENTOR',
                is_active=True,
            ).exists()
            if not is_authorized:
                return CustomResponse(
                    general_message="You are not authorized for this task's interest group"
                ).get_failure_response(
                    status_code=403,
                    http_status_code=403,
                )

        raw_status = request.data.get("status")
        action_status = str(raw_status).upper() if raw_status else ""
        if action_status not in ("APPROVED", "REJECTED"):
            return CustomResponse(
                general_message="status is required and must be 'APPROVED' or 'REJECTED'"
            ).get_failure_response()

        feedback = request.data.get("feedback")
        if feedback is not None:
            if not isinstance(feedback, str):
                return CustomResponse(
                    general_message="feedback must be a string"
                ).get_failure_response()
            if len(feedback) > 500:
                return CustomResponse(
                    general_message="feedback must be 500 characters or less"
                ).get_failure_response()

        log_entry.mentor_review_status = action_status
        log_entry.mentor_reviewed_by_id = user_id
        log_entry.mentor_reviewed_at = timezone.now()
        log_entry.mentor_review_feedback = feedback
        log_entry.updated_by_id = user_id
        log_entry.save()

        action_word = "approved" if action_status == "APPROVED" else "rejected"
        return CustomResponse(
            general_message=f"Task {action_word} successfully"
        ).get_success_response()
