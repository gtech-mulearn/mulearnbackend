from django.db.models import Count, Max, F, Q, Subquery, OuterRef
from rest_framework.views import APIView

from db.user import User, UserMentor
from db.task import (
    KarmaActivityLog, UserIgLink, UserIgLvlLink,
    Wallet, UserLvlLink, InterestGroup, MentorSession
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
        """List sessions for the authenticated mentor."""
        user_id = JWTUtils.fetch_user_id(request)

        sessions = MentorSession.objects.filter(
            mentor_id=user_id
        ).select_related("mentee", "ig")

        params = request.query_params

        if status := params.get("status"):
            sessions = sessions.filter(status=status)

        if date_from := params.get("date_from"):
            sessions = sessions.filter(scheduled_at__date__gte=date_from)

        if date_to := params.get("date_to"):
            sessions = sessions.filter(scheduled_at__date__lte=date_to)

        paginated = CommonUtils.get_paginated_queryset(
            sessions,
            request,
            search_fields=["title"],
            sort_fields={
                "scheduled_at": "scheduled_at",
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
        """Create a new session — verified mentors only."""
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
            mentor_ig_ids = UserIgLink.objects.filter(
                user_id=user_id
            ).values_list("ig_id", flat=True)
            if ig_id not in mentor_ig_ids:
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
        """Update session status (complete/cancel) and notes."""
        if not session_id:
            return CustomResponse(
                general_message="session_id is required"
            ).get_failure_response()

        user_id = JWTUtils.fetch_user_id(request)

        session = MentorSession.objects.filter(id=session_id).first()
        if session is None:
            return CustomResponse(
                general_message="Session not found"
            ).get_failure_response()

        if session.mentor_id != user_id:
            return CustomResponse(
                general_message="Not your session to update"
            ).get_failure_response(
                status_code=403,
                http_status_code=403,
            )

        serializer = mentorship_serializers.MentorSessionUpdateSerializer(
            session, data=request.data, partial=True,
            context={"user_id": user_id},
        )
        if serializer.is_valid():
            serializer.save()
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

        session_qs = MentorSession.objects.filter(mentor_id=user_id)
        if ig_id:
            session_qs = session_qs.filter(ig_id=ig_id)

        mentee_stats = (
            session_qs
            .values("mentee_id")
            .annotate(
                session_count=Count("id"),
                last_session_at=Max("scheduled_at"),
            )
        )

        mentee_ids = [m["mentee_id"] for m in mentee_stats]
        stats_map = {m["mentee_id"]: m for m in mentee_stats}

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
        """Task verification queue filtered by mentor's IGs."""
        user_id = JWTUtils.fetch_user_id(request)

        # Guard: verified mentor only
        mentor = UserMentor.objects.filter(user_id=user_id).first()
        if mentor is None or not mentor.is_verified:
            return CustomResponse(
                general_message="Only verified mentors can access the task queue"
            ).get_failure_response(
                status_code=403,
                http_status_code=403,
            )

        mentor_ig_ids = list(
            UserIgLink.objects.filter(user_id=user_id)
            .values_list("ig_id", flat=True)
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

        status_filter = params.get("status", "pending")
        if status_filter == "pending":
            logs = logs.filter(appraiser_approved__isnull=True)
        elif status_filter == "approved":
            logs = logs.filter(appraiser_approved=True)
        elif status_filter == "rejected":
            logs = logs.filter(appraiser_approved=False)

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
        """Approve or reject a pending task."""
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

        if log_entry.appraiser_approved is not None:
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
            ).exists()
            if not is_authorized:
                return CustomResponse(
                    general_message="You are not authorized for this task's interest group"
                ).get_failure_response(
                    status_code=403,
                    http_status_code=403,
                )

        action_status = request.data.get("status")
        if action_status not in ("approved", "rejected"):
            return CustomResponse(
                general_message="status is required and must be 'approved' or 'rejected'"
            ).get_failure_response()

        remarks = request.data.get("remarks")

        log_entry.appraiser_approved = (action_status == "approved")
        log_entry.appraiser_approved_by_id = user_id
        log_entry.remarks = remarks
        log_entry.updated_by_id = user_id
        log_entry.save()

        action_word = "approved" if action_status == "approved" else "rejected"
        return CustomResponse(
            general_message=f"Task {action_word} successfully"
        ).get_success_response()
