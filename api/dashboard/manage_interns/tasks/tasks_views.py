import json
from rest_framework.views import APIView
from django.utils.timezone import now

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.intern import InternTask
from .serializers import ManageInternTaskSerializer

class ManageInternTaskAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, task_id=None):
        if task_id:
            task = InternTask.objects.filter(id=task_id).first()
            if not task:
                return CustomResponse(general_message="Task not found.").get_failure_response()
            serializer = ManageInternTaskSerializer(task)
            return CustomResponse(response=serializer.data).get_success_response()
            
        tasks = InternTask.objects.all().order_by('-created_at')
        
        paginated_queryset = CommonUtils.get_paginated_queryset(
            tasks, request,
            ['title', 'status', 'category', 'assigned_to__full_name'],
            {'created_at': 'created_at', 'status': 'status'}
        )
        
        serializer = ManageInternTaskSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = ManageInternTaskSerializer(data=request.data, context={'user_id': user_id})
        
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message="Task created successfully.").get_success_response()
            
        return CustomResponse(response=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, task_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        task = InternTask.objects.filter(id=task_id).first()
        if not task:
            return CustomResponse(general_message="Task not found.").get_failure_response()
            
        request_data = request.data
            
        old_data = {
            "title": task.title,
            "description": task.description,
            "category": task.category,
            "complexity": task.complexity,
            "assigned_to_id": task.assigned_to_id,
            "status": task.status
        }
            
        serializer = ManageInternTaskSerializer(task, data=request_data, partial=True, context={'user_id': user_id})
        
        if serializer.is_valid():
            serializer.save()
            
            from db.mentor import SystemActionLog
            new_data = {k: v for k, v in request_data.items() if k in old_data}
            
            if new_data:
                SystemActionLog.objects.create(
                    action_type=SystemActionLog.ActionType.INTERN_TASK_UPDATE.value,
                    actor_user_id=user_id,
                    subject_user_id=task.assigned_to_id,
                    entity_name='intern_task',
                    entity_id=task.id,
                    old_data=old_data,
                    new_data=new_data
                )
            
            return CustomResponse(general_message="Task updated successfully.").get_success_response()
            
        return CustomResponse(response=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, task_id):
        task = InternTask.objects.filter(id=task_id).first()
        if not task:
            return CustomResponse(general_message="Task not found.").get_failure_response()
            
        task.delete()
        return CustomResponse(general_message="Task deleted successfully.").get_success_response()
