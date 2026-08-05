from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternTaskCategory, InternTaskStatus
from utils.utils import CommonUtils
from db.intern import InternTask
from .serializers import InternTaskSerializer


class InternTaskCategoryAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value,RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve all intern task categories and their sub-categories.",
        responses={200: OpenApiResponse(description="Task categories retrieved successfully.")},
    )
    def get(self, request):
        categories = {
            member.name.replace("_", " ").title(): member.value
            for member in InternTaskCategory
        }
        return CustomResponse(response=categories).get_success_response()


class InternTaskDetailAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve detail for a specific task assigned to the current intern.",
        responses={200: InternTaskSerializer},
    )
    def get(self, request, task_id):
        user_id = JWTUtils.fetch_user_id(request)
        task = InternTask.objects.filter(id=task_id, assigned_to_id=user_id).first()
        if not task:
            return CustomResponse(general_message="Task not found.").get_failure_response()
        serializer = InternTaskSerializer(task)
        return CustomResponse(response=serializer.data).get_success_response()


class InternTaskSubmitAPI(APIView):
    """
    Allows an intern to directly set task status and output_link
    without going through a timesheet submission.
    """
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Directly submit a task update: set status and/or output_link. "
            "output_link is required when status=COMPLETED."
        ),
        responses={200: OpenApiResponse(description="Task submitted successfully.")},
    )
    def patch(self, request, task_id):
        user_id = JWTUtils.fetch_user_id(request)
        task = InternTask.objects.filter(id=task_id, assigned_to_id=user_id).first()

        if not task:
            return CustomResponse(general_message="Task not found.").get_failure_response()

        if task.is_verified:
            return CustomResponse(general_message="Task is already verified and cannot be modified.").get_failure_response()

        status = request.data.get('status')
        output_link = request.data.get('output_link')

        if not status and output_link is None:
            return CustomResponse(general_message="At least one of status or output_link is required.").get_failure_response()

        editable = InternTaskStatus.intern_editable()
        if status and status not in editable:
            return CustomResponse(general_message=f"Invalid status '{status}'. Valid values: {editable}").get_failure_response()

        if status == InternTaskStatus.COMPLETED.value:
            resolved_link = output_link or task.output_link
            if not resolved_link:
                return CustomResponse(general_message="output_link is required when marking a task as COMPLETED.").get_failure_response()

        old_data = {'status': task.status, 'output_link': task.output_link}
        if status:
            task.status = status
        if output_link is not None:
            task.output_link = output_link
        task.save(update_fields=['status', 'output_link'] if output_link is not None else ['status'])

        from db.mentor import SystemActionLog
        SystemActionLog.objects.create(
            action_type=SystemActionLog.ActionType.INTERN_TASK_UPDATE.value,
            actor_user_id=user_id,
            subject_user_id=user_id,
            entity_name='intern_task',
            entity_id=task.id,
            old_data=old_data,
            new_data={'status': task.status, 'output_link': task.output_link}
        )

        return CustomResponse(general_message="Task status updated successfully.").get_success_response()

class InternTaskMineAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve all tasks assigned to the current intern.",
        responses={200: InternTaskSerializer(many=True)},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        tasks = InternTask.objects.filter(assigned_to_id=user_id).order_by('-created_at')

        paginated_queryset = CommonUtils.get_paginated_queryset(
            tasks, request,
            ['title', 'status'],
            {'created_at': 'created_at', 'status': 'status'}
        )

        serializer = InternTaskSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()
