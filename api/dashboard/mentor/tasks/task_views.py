from django.utils import timezone
from rest_framework.views import APIView

from db.user import UserMentor, UserRoleLink
from db.task import KarmaActivityLog
from utils.permission import CustomizePermission, JWTUtils
from utils.mentor_permissions import IsIGMentor, IsVerifiedIGMentor, _get_persona_context
from utils.response import CustomResponse
from utils.utils import CommonUtils
from .serializers import TaskQueueSerializer


class MentorTaskQueueView(APIView):
    """
    GET /api/v1/dashboard/mentor/tasks/queue/

    Returns a paginated list of KarmaActivityLog entries for tasks submitted
    by learners in the mentor's active IG, pending mentor review.

    Restricted to verified mentors only.

    Query params:
        ig_id   - optional override (defaults to active persona IG)
        status  - PENDING (default) | APPROVED | REJECTED
    """
    permission_classes = [CustomizePermission, IsVerifiedIGMentor]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        persona_ctx = _get_persona_context(request)

        # Derive active IG from persona context; allow override via query param
        active_ig_id = request.query_params.get("ig_id") or persona_ctx['ig_id']

        # Confirm this mentor actually has a Mentor role for the requested IG
        is_authorized_for_ig = UserRoleLink.objects.filter(
            user_id=user_id,
            ig_id=active_ig_id,
            role__title='Mentor',
            is_active=True,
        ).exists()
        if not is_authorized_for_ig:
            return CustomResponse(
                general_message="You are not authorized as a mentor for this interest group"
            ).get_failure_response()

        logs = (
            KarmaActivityLog.objects
            .filter(task__ig_id=active_ig_id)
            .select_related("user", "task", "task__ig")
        )

        allowed_statuses = {"PENDING", "APPROVED", "REJECTED"}
        status_filter = request.query_params.get("status", "PENDING").upper()
        if status_filter not in allowed_statuses:
            return CustomResponse(
                general_message="Invalid status filter. Must be PENDING, APPROVED, or REJECTED"
            ).get_failure_response()

        logs = logs.filter(mentor_review_status=status_filter).order_by("-created_at")

        paginated = CommonUtils.get_paginated_queryset(
            logs,
            request,
            search_fields=["user__full_name", "task__title"],
            sort_fields={"created_at": "created_at"},
        )

        serializer = TaskQueueSerializer(paginated["queryset"], many=True)
        return CustomResponse(
            response={
                "active_ig_id": active_ig_id,
                "data": serializer.data,
                "pagination": paginated["pagination"],
            }
        ).get_success_response()


class MentorTaskActionView(APIView):
    """
    PATCH /api/v1/dashboard/mentor/tasks/queue/<log_id>/

    Approve or reject a pending task submission.
    - Sets mentor_review_status to APPROVED or REJECTED.
    - Does NOT credit karma — that remains the appraiser's responsibility.
    - Restricted to verified mentors with a Mentor role in the task's IG.

    Body:
        status   : "APPROVED" | "REJECTED"  (required)
        feedback : string ≤ 500 chars        (optional)
    """
    permission_classes = [CustomizePermission, IsVerifiedIGMentor]

    def patch(self, request, log_id):
        user_id = JWTUtils.fetch_user_id(request)

        log_entry = (
            KarmaActivityLog.objects
            .filter(id=log_id)
            .select_related("task", "task__ig")
            .first()
        )
        if log_entry is None:
            return CustomResponse(
                general_message="Karma log entry not found"
            ).get_failure_response()

        if log_entry.mentor_review_status != "PENDING":
            return CustomResponse(
                general_message="This task has already been actioned"
            ).get_failure_response()

        # Confirm mentor has a Mentor role for the task's IG
        if log_entry.task and log_entry.task.ig:
            is_authorized = UserRoleLink.objects.filter(
                user_id=user_id,
                ig_id=log_entry.task.ig_id,
                role__title='Mentor',
                is_active=True,
            ).exists()
            if not is_authorized:
                return CustomResponse(
                    general_message="You are not authorized as a mentor for this task's interest group"
                ).get_failure_response()

        # Validate action
        raw_status = request.data.get("status")
        action_status = str(raw_status).upper() if raw_status else ""
        if action_status not in ("APPROVED", "REJECTED"):
            return CustomResponse(
                general_message="status is required and must be 'APPROVED' or 'REJECTED'"
            ).get_failure_response()

        # Validate optional feedback
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

        # Record mentor's review — karma credit remains with the appraiser flow
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
