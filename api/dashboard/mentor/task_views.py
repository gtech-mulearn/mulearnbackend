import json
import uuid

from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiResponse, inline_serializer
from rest_framework import serializers as s

from db.task import TaskList, InterestGroup, UserIgLink
from db.skill import Skill, TaskSkillLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils, DateTimeUtils

from .task_serializers import (
    MentorIGDropdownSerializer,
    MentorTaskCreateSerializer,
    MentorTaskListSerializer,
    MentorTaskUpdateSerializer,
)

def _save_task_skills(task_id, skill_ids, user_id):
    """Clear and re-create TaskSkillLink rows — mirrors admin implementation."""
    TaskSkillLink.objects.filter(task_id=task_id).delete()
    for skill_id in skill_ids:
        if Skill.objects.filter(id=skill_id, is_active=True).exists():
            TaskSkillLink.objects.create(
                id=str(uuid.uuid4()),
                task_id=task_id,
                skill_id=skill_id,
                created_by_id=user_id,
            )

class MentorIGDropdownAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Mentor Task"],
        description=(
            "Returns only the Interest Groups the authenticated mentor "
            "belongs to (active MENTOR assignment). "
            "Use this list to populate the IG selector when creating a task."
        ),
        responses={
            200: inline_serializer(
                "MentorIGDropdownResponse",
                fields={
                    "id":   s.CharField(),
                    "name": s.CharField(),
                },
                many=True,
            )
        },
    )
    @role_required([RoleType.MENTOR.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        ig_ids = UserIgLink.objects.filter(
            user_id=user_id,
            assignment_type=UserIgLink.AssignmentType.MENTOR,
            is_active=True,
        ).values_list("ig_id", flat=True)

        igs = InterestGroup.objects.filter(id__in=ig_ids).values("id", "name")
        return CustomResponse(response=list(igs)).get_success_response()

class MentorTaskListCreateAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Mentor Task"],
        description=(
            "List all tasks submitted by the authenticated mentor "
            "(filtered by requested_by). Supports pagination, search, and sort."
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
                "MentorTaskListResponse",
                fields={
                    "data":       s.ListField(child=s.DictField()),
                    "pagination": s.DictField(),
                },
            )
        },
    )
    @role_required([RoleType.MENTOR.value])
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

        serializer = MentorTaskListSerializer(
            paginated.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated.get("pagination"),
        )

    @extend_schema(
        tags=["Dashboard - Mentor Task"],
        description=(
            "Create a new task for an IG the mentor belongs to. "
            "The task is saved with approval_status='pending' and active=False "
            "until an admin approves it. "
            "Accepts an optional skill_ids list (array of active skill UUIDs) "
            "alongside the task fields — mirrors admin task creation behaviour."
        ),
        request=MentorTaskCreateSerializer,
        responses={200: OpenApiResponse(description="Task submitted for approval.")},
    )
    @role_required([RoleType.MENTOR.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        from db.user import UserMentor
        mentor_profile = UserMentor.objects.filter(user_id=user_id).first()
        if mentor_profile and not mentor_profile.is_active:
            return CustomResponse(
                general_message="Your mentor account is deactivated. Please contact an administrator."
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

        serializer = MentorTaskCreateSerializer(
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


class MentorTaskDetailAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Mentor Task"],
        description="Retrieve the detail of a specific task submitted by the mentor.",
        responses={200: MentorTaskListSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    def get(self, request, task_id):
        user_id = JWTUtils.fetch_user_id(request)

        task = TaskList.objects.select_related(
            "channel", "type", "level", "ig", "org", "requested_by"
        ).filter(id=task_id, requested_by_id=user_id).first()

        if not task:
            return CustomResponse(
                general_message="Task not found."
            ).get_failure_response(status_code=404)

        serializer = MentorTaskListSerializer(task)
        return CustomResponse(response=serializer.data).get_success_response()

    @extend_schema(
        tags=["Dashboard - Mentor Task"],
        description=(
            "Update a task submitted by the mentor. "
            "Regardless of the current approval_status, the task reverts to "
            "'pending' and active=False after editing (triggering re-approval). "
            "If the task was previously approved, it is deactivated until re-approved. "
            "Accepts optional skill_ids to replace the current skill links."
        ),
        request=MentorTaskUpdateSerializer,
        responses={200: OpenApiResponse(description="Task updated and re-submitted for approval.")},
    )
    @role_required([RoleType.MENTOR.value])
    def put(self, request, task_id):
        user_id = JWTUtils.fetch_user_id(request)

        from db.user import UserMentor
        mentor_profile = UserMentor.objects.filter(user_id=user_id).first()
        if mentor_profile and not mentor_profile.is_active:
            return CustomResponse(
                general_message="Your mentor account is deactivated. Please contact an administrator."
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

        serializer = MentorTaskUpdateSerializer(
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
        tags=["Dashboard - Mentor Task"],
        description=(
            "Delete a task submitted by the mentor. "
            "Only allowed when approval_status is 'pending'. "
            "Approved or rejected tasks cannot be deleted."
        ),
        responses={200: OpenApiResponse(description="Task deleted successfully.")},
    )
    @role_required([RoleType.MENTOR.value])
    def delete(self, request, task_id):
        user_id = JWTUtils.fetch_user_id(request)

        from db.user import UserMentor
        mentor_profile = UserMentor.objects.filter(user_id=user_id).first()
        if mentor_profile and not mentor_profile.is_active:
            return CustomResponse(
                general_message="Your mentor account is deactivated. Please contact an administrator."
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
