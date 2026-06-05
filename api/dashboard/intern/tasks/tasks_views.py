from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.intern import InternTask
from .serializers import InternTaskSerializer

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
            ['title', 'status', 'category'],
            {'created_at': 'created_at', 'status': 'status'}
        )
        
        serializer = InternTaskSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Update the status of an intern task.",
        responses={200: OpenApiResponse(description="Task status updated successfully.")},
    )
    def patch(self, request, task_id):
        user_id = JWTUtils.fetch_user_id(request)
        task = InternTask.objects.filter(id=task_id, assigned_to_id=user_id).first()
        
        if not task:
            return CustomResponse(general_message="Task not found.").get_failure_response()
            
        status = request.data.get('status')
        if not status:
            return CustomResponse(general_message="Status is required.").get_failure_response()
            
        old_data = {"status": task.status}
        
        serializer = InternTaskSerializer(task, data={'status': status}, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            from db.mentor import SystemActionLog
            SystemActionLog.objects.create(
                action_type=SystemActionLog.ActionType.INTERN_TASK_UPDATE.value,
                actor_user_id=user_id,
                subject_user_id=user_id,
                entity_name='intern_task',
                entity_id=task.id,
                old_data=old_data,
                new_data={'status': status}
            )
            
            return CustomResponse(general_message="Task status updated successfully.").get_success_response()
        return CustomResponse(response=serializer.errors).get_failure_response()
