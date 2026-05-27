import uuid

from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView

from db.company import Company, CompanyUserLink
from db.task import (
    Channel, InterestGroup, Level, TaskList, TaskType,
)
from db.user import User, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils

from .serializers import CompanyTaskListSerializer, CompanyTaskSubmitSerializer


# ---------------------------------------------------------------------------
# Shared helpers (mirrors pattern in jobs module)
# ---------------------------------------------------------------------------

def _get_company_user(request):
    """Return (user, company, error_response). error_response is None on success."""
    try:
        user_id = JWTUtils.fetch_user_id(request)
    except Exception:
        return None, None, CustomResponse(
            general_message="User not found or token invalid.",
            message={"error_code": "USER_NOT_FOUND"},
        ).get_failure_response(status_code=401, http_status_code=status.HTTP_401_UNAUTHORIZED)

    user = User.objects.filter(id=user_id).first()
    if not user:
        return None, None, CustomResponse(
            general_message="User not found.",
            message={"error_code": "USER_NOT_FOUND"},
        ).get_failure_response(status_code=401, http_status_code=status.HTTP_401_UNAUTHORIZED)

    if not UserRoleLink.objects.filter(user=user, role__title=RoleType.COMPANY.value).exists():
        return None, None, CustomResponse(
            general_message="Company role required.",
            message={"error_code": "COMPANY_ROLE_REQUIRED"},
        ).get_failure_response(status_code=403, http_status_code=status.HTTP_403_FORBIDDEN)

    company = Company.objects.filter(company_user_id=user, status="active", deleted_at__isnull=True).first()
    if not company:
        return None, None, CustomResponse(
            general_message="No active company found for this user.",
            message={"error_code": "NO_ACTIVE_COMPANY"},
        ).get_failure_response(status_code=403, http_status_code=status.HTTP_403_FORBIDDEN)

    return user, company, None


# ---------------------------------------------------------------------------
# Company: Submit a new task for admin review
# ---------------------------------------------------------------------------

class CompanyTaskSubmitAPIView(APIView):
    """
    POST /company/tasks/submit/

    Company submits a new task. It is created with approval_status='pending'
    and active=False — it becomes live only after admin approval.
    """
    permission_classes = [CustomizePermission]

    def post(self, request):
        user, company, err = _get_company_user(request)
        if err:
            return err

        serializer = CompanyTaskSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                general_message="Invalid task submission data.",
                message={"error_code": "VALIDATION_ERROR", "errors": serializer.errors},
            ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Resolve optional FKs
        channel = None
        if data.get("channel_id"):
            channel = Channel.objects.filter(id=data["channel_id"]).first()

        level = None
        if data.get("level_id"):
            level = Level.objects.filter(id=data["level_id"]).first()

        ig = InterestGroup.objects.get(id=data["ig_id"])
        task_type = TaskType.objects.get(id=data["type_id"])

        task = TaskList.objects.create(
            id=str(uuid.uuid4()),
            hashtag=data["hashtag"],
            title=data["title"],
            description=data.get("description") or None,
            karma=data["karma"],
            ig=ig,
            type=task_type,
            channel=channel,
            level=level,
            active=False,
            approval_status="pending",
            submitted_by_company=company,
            created_by=user,
            updated_by=user,
        )

        return CustomResponse(
            general_message="Task submitted for admin review.",
            response=CompanyTaskListSerializer(task).data,
        ).get_success_response()


# ---------------------------------------------------------------------------
# Company: List their submitted tasks
# ---------------------------------------------------------------------------

class CompanyTaskListAPIView(APIView):
    """
    GET /company/tasks/

    Returns a paginated list of all tasks submitted by the authenticated company.
    Optional filter: ?approval_status=pending|approved|rejected
    """
    permission_classes = [CustomizePermission]

    def get(self, request):
        user, company, err = _get_company_user(request)
        if err:
            return err

        queryset = (
            TaskList.objects
            .filter(submitted_by_company=company)
            .select_related("ig", "type")
            .order_by("-created_at")
        )

        approval_status = request.query_params.get("approval_status")
        if approval_status:
            valid = [c[0] for c in TaskList.APPROVAL_STATUS_CHOICES]
            if approval_status not in valid:
                return CustomResponse(
                    general_message=f"Invalid approval_status. Valid values: {valid}",
                    message={"error_code": "INVALID_FILTER"},
                ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(approval_status=approval_status)

        paginated = CommonUtils.get_paginated_queryset(
            queryset=queryset,
            request=request,
            search_fields=["title", "hashtag"],
            sort_fields={"createdAt": "created_at", "title": "title"},
            is_pagination=True,
        )

        serializer = CompanyTaskListSerializer(list(paginated["queryset"]), many=True)
        return CustomResponse(
            general_message="Tasks fetched successfully.",
            response={"tasks": serializer.data, "pagination": paginated["pagination"]},
        ).get_success_response()


# ---------------------------------------------------------------------------
# Company: Resubmit a rejected task
# ---------------------------------------------------------------------------

class CompanyTaskResubmitAPIView(APIView):
    """
    POST /company/tasks/<task_id>/resubmit/

    Resets a rejected task back to pending review (no new row created).
    Only the submitting company can resubmit.
    """
    permission_classes = [CustomizePermission]

    def post(self, request, task_id):
        user, company, err = _get_company_user(request)
        if err:
            return err

        try:
            task = TaskList.objects.get(id=task_id, submitted_by_company=company)
        except TaskList.DoesNotExist:
            return CustomResponse(
                general_message="Task not found.",
                message={"error_code": "TASK_NOT_FOUND"},
            ).get_failure_response(status_code=404, http_status_code=status.HTTP_404_NOT_FOUND)

        if task.approval_status != "rejected":
            return CustomResponse(
                general_message=f"Only rejected tasks can be resubmitted. Current status: '{task.approval_status}'.",
                message={"error_code": "INVALID_STATUS_TRANSITION"},
            ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

        task.approval_status = "pending"
        task.active = False
        task.rejection_reason = None
        task.reviewed_by_admin = None
        task.reviewed_at = None
        task.updated_by = user
        task.save(update_fields=[
            "approval_status", "active", "rejection_reason",
            "reviewed_by_admin", "reviewed_at", "updated_by", "updated_at",
        ])

        return CustomResponse(
            general_message="Task resubmitted for admin review.",
            response=CompanyTaskListSerializer(task).data,
        ).get_success_response()
