import json
import uuid

from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiResponse, inline_serializer
from rest_framework import serializers as s

from db.task import TaskList
from db.skill import Skill, TaskSkillLink
from db.company import Company
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils, DateTimeUtils

from .task_serializers import (
    CompanyTaskCreateSerializer,
    CompanyTaskListSerializer,
    CompanyTaskUpdateSerializer,
)


def _save_task_skills(task_id, skill_ids, user_id):
    """Clear and re-create TaskSkillLink rows."""
    TaskSkillLink.objects.filter(task_id=task_id).delete()
    for skill_id in skill_ids:
        if Skill.objects.filter(id=skill_id, is_active=True).exists():
            TaskSkillLink.objects.create(
                id=str(uuid.uuid4()),
                task_id=task_id,
                skill_id=skill_id,
                created_by_id=user_id,
            )


def get_verified_company(user_id):
    """
    Return the verified Company for a user if they are:
    - the company creator (company_user_id == user_id), OR
    - an approved COMPANY_MENTOR for that company.
    """
    company = Company.objects.filter(company_user_id=user_id, status="verified").first()
    if company:
        return company

    from db.user import UserMentor
    mentor = UserMentor.objects.filter(
        user_id=user_id,
        mentor_tier=UserMentor.MentorTier.COMPANY_MENTOR,
        status=UserMentor.Status.APPROVED,
    ).select_related("org").first()

    if mentor and mentor.org:
        return Company.objects.filter(name=mentor.org.title, status="verified").first()

    return None


class CompanyTaskListCreateAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Company Task"],
        description=(
            "List all tasks submitted by the authenticated company user "
            "(creator or company mentor). Supports pagination, search, and sort."
        ),
        parameters=[
            OpenApiParameter(
                "approval_status",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                required=False,
                description="Filter by approval_status: pending | approved | rejected",
            ),
        ],
        responses={
            200: inline_serializer(
                "CompanyTaskListResponse",
                fields={
                    "data":       s.ListField(child=s.DictField()),
                    "pagination": s.DictField(),
                },
            )
        },
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        queryset = TaskList.objects.select_related(
            "channel", "type", "level", "ig", "org", "requested_by"
        ).filter(requested_by_id=user_id)

        approval_status = request.query_params.get("approval_status")
        if approval_status:
            queryset = queryset.filter(approval_status=approval_status)

        paginated = CommonUtils.get_paginated_queryset(
            queryset,
            request,
            search_fields=[
                "hashtag",
                "title",
                "description",
                "karma",
                "ig__name",
                "type__title",
                "approval_status",
            ],
            sort_fields={
                "hashtag":          "hashtag",
                "title":            "title",
                "karma":            "karma",
                "ig":               "ig__name",
                "type":             "type__title",
                "approval_status":  "approval_status",
                "created_at":       "created_at",
                "updated_at":       "updated_at",
            },
        )

        serializer = CompanyTaskListSerializer(
            paginated.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated.get("pagination"),
        )

    @extend_schema(
        tags=["Dashboard - Company Task"],
        description=(
            "Create a new task for the company. "
            "The task is saved with approval_status='pending' and active=False "
            "until an admin approves it. "
            "Accepts an optional skill_ids list."
        ),
        request=CompanyTaskCreateSerializer,
        responses={200: OpenApiResponse(description="Task submitted for approval.")},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        company = get_verified_company(user_id)
        if not company:
            return CustomResponse(
                general_message="You must have a verified company profile to submit tasks."
            ).get_failure_response(status_code=403)

        mutable_data = request.data.copy()
        mutable_data["created_by"] = user_id
        mutable_data["updated_by"] = user_id

        skill_ids = mutable_data.pop("skill_ids", None)
        if isinstance(skill_ids, str):
            try:
                skill_ids = json.loads(skill_ids)
            except (json.JSONDecodeError, TypeError):
                skill_ids = []

        serializer = CompanyTaskCreateSerializer(
            data=mutable_data,
            context={"user_id": user_id},
        )
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        task = serializer.save(
            id=str(uuid.uuid4()),
            approval_status="pending",
            active=False,
            requested_by_id=user_id,
            requested_at=DateTimeUtils.get_current_utc_time(),
        )

        if skill_ids:
            _save_task_skills(task.id, skill_ids, user_id)

        return CustomResponse(
            general_message="Task submitted for approval."
        ).get_success_response()


class CompanyTaskDetailAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Company Task"],
        description="Retrieve the detail of a specific task submitted by the company.",
        responses={200: CompanyTaskListSerializer},
    )
    def get(self, request, task_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = get_verified_company(user_id)
        if not company:
            return CustomResponse(
                general_message="Access denied. Verified company profile required."
            ).get_failure_response(status_code=403)

        task = TaskList.objects.select_related(
            "channel", "type", "level", "ig", "org", "requested_by"
        ).filter(id=task_id, requested_by_id=user_id).first()

        if not task:
            return CustomResponse(
                general_message="Task not found."
            ).get_failure_response(status_code=404)

        serializer = CompanyTaskListSerializer(task)
        return CustomResponse(response=serializer.data).get_success_response()

    @extend_schema(
        tags=["Dashboard - Company Task"],
        description=(
            "Update a task submitted by the company. "
            "Regardless of the current approval_status, the task reverts to "
            "'pending' and active=False after editing."
        ),
        request=CompanyTaskUpdateSerializer,
        responses={200: OpenApiResponse(description="Task updated and re-submitted for approval.")},
    )
    def put(self, request, task_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = get_verified_company(user_id)
        if not company:
            return CustomResponse(
                general_message="Access denied. Verified company profile required."
            ).get_failure_response(status_code=403)

        task = TaskList.objects.filter(
            id=task_id, requested_by_id=user_id
        ).first()

        if not task:
            return CustomResponse(
                general_message="Task not found."
            ).get_failure_response(status_code=404)

        mutable_data = request.data.copy()
        mutable_data["updated_by"] = user_id

        skill_ids = mutable_data.pop("skill_ids", None)
        if isinstance(skill_ids, str):
            try:
                skill_ids = json.loads(skill_ids)
            except (json.JSONDecodeError, TypeError):
                skill_ids = None

        serializer = CompanyTaskUpdateSerializer(
            task,
            data=mutable_data,
            partial=True,
            context={"user_id": user_id},
        )
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        serializer.save(
            approval_status="pending",
            active=False,
            rejection_reason=None,
            reviewed_by_admin=None,
            reviewed_at=None,
        )

        if skill_ids is not None:
            _save_task_skills(task_id, skill_ids, user_id)

        return CustomResponse(
            general_message="Task updated and re-submitted for approval."
        ).get_success_response()

    @extend_schema(
        tags=["Dashboard - Company Task"],
        description="Delete a pending task submitted by the company.",
        responses={200: OpenApiResponse(description="Task deleted successfully.")},
    )
    def delete(self, request, task_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = get_verified_company(user_id)
        if not company:
            return CustomResponse(
                general_message="Access denied. Verified company profile required."
            ).get_failure_response(status_code=403)

        task = TaskList.objects.filter(
            id=task_id, requested_by_id=user_id
        ).first()

        if not task:
            return CustomResponse(
                general_message="Task not found."
            ).get_failure_response(status_code=404)

        if task.approval_status != "pending":
            return CustomResponse(
                general_message=(
                    f"Cannot delete a task with status '{task.approval_status}'. "
                    "Only pending tasks can be deleted."
                )
            ).get_failure_response()

        task.delete()
        return CustomResponse(
            general_message="Task deleted successfully."
        ).get_success_response()
