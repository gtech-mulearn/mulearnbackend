import json
import uuid
from rest_framework.views import APIView
from django.utils.timezone import now
from django.db import transaction
from django.db.models import F
from drf_spectacular.utils import extend_schema, OpenApiResponse

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternHashtag
from utils.utils import CommonUtils
from db.intern import InternTask
from db.task import KarmaActivityLog, TaskList, Wallet
from .serializers import ManageInternTaskSerializer

class ManageInternTaskAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, RoleType.INTERN.value, RoleType.INTERN_LEAD.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve intern task(s) or task detail.",
        responses={200: ManageInternTaskSerializer(many=True)},
    )
    def get(self, request, task_id=None):
        if task_id:
            task = InternTask.objects.filter(id=task_id).first()
            if not task:
                return CustomResponse(general_message="Task not found.").get_failure_response()
            serializer = ManageInternTaskSerializer(task)
            return CustomResponse(response=serializer.data).get_success_response()
            
        tasks = InternTask.objects.select_related('assigned_to').all().order_by('-created_at')
        
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

    @role_required([RoleType.ADMIN.value, RoleType.INTERN.value, RoleType.INTERN_LEAD.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Create an intern task.",
        responses={200: OpenApiResponse(description="Task created successfully.")},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = ManageInternTaskSerializer(data=request.data, context={'user_id': user_id})
        
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message="Task created successfully.").get_success_response()
            
        return CustomResponse(response=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value, RoleType.INTERN.value, RoleType.INTERN_LEAD.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Update an intern task (partial update).",
        responses={200: OpenApiResponse(description="Task updated successfully.")},
    )
    def patch(self, request, task_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        task = InternTask.objects.filter(id=task_id).first()
        if not task:
            return CustomResponse(general_message="Task not found.").get_failure_response()
            
        if task.is_verified:
            return CustomResponse(general_message="Task is already verified and cannot be edited.").get_failure_response()
            
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

    @role_required([RoleType.ADMIN.value, RoleType.INTERN.value, RoleType.INTERN_LEAD.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Delete an intern task.",
        responses={200: OpenApiResponse(description="Task deleted successfully.")},
    )
    def delete(self, request, task_id):
        task = InternTask.objects.filter(id=task_id).first()
        if not task:
            return CustomResponse(general_message="Task not found.").get_failure_response()

        if task.is_verified:
            return CustomResponse(general_message="Cannot delete a verified task. Revoke verification first.").get_failure_response()

        task.delete()
        return CustomResponse(general_message="Task deleted successfully.").get_success_response()

class ManageInternTasksByInternAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, RoleType.INTERN.value, RoleType.INTERN_LEAD.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve all tasks assigned to a specific intern identified by their muid.",
        responses={200: ManageInternTaskSerializer(many=True)},
    )
    def get(self, request, muid):
        from db.user import User
        user = User.objects.filter(muid=muid).first()
        if not user:
            return CustomResponse(general_message=f"User with muid '{muid}' not found.").get_failure_response()

        tasks = InternTask.objects.select_related('assigned_to').filter(assigned_to_id=user.id).order_by('-created_at')

        paginated_queryset = CommonUtils.get_paginated_queryset(
            tasks, request,
            ['title', 'status', 'category'],
            {'created_at': 'created_at', 'status': 'status', 'deadline': 'deadline'}
        )

        serializer = ManageInternTaskSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()

class ManageInternTaskVerifyAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, RoleType.INTERN.value, RoleType.INTERN_LEAD.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Verify an intern task and award karma.",
        responses={200: OpenApiResponse(description="Task verified successfully.")},
    )
    def post(self, request, task_id):
        admin_id = JWTUtils.fetch_user_id(request)

        task = InternTask.objects.filter(id=task_id).first()
        if not task:
            return CustomResponse(general_message="Task not found.").get_failure_response()

        if task.is_verified:
            return CustomResponse(general_message="Task is already verified.").get_failure_response()

        karma_awarded = request.data.get('karma_awarded', 0)
        try:
            karma_awarded = int(karma_awarded)
        except (ValueError, TypeError):
            return CustomResponse(general_message="karma_awarded must be an integer.").get_failure_response()

        intern_user_id = task.assigned_to_id

        with transaction.atomic():
            task.is_verified = True
            task.verified_by_id = admin_id
            task.karma_awarded = karma_awarded
            task.save()

            # Award karma to intern's wallet and log it.
            if karma_awarded > 0:
                task_list = TaskList.objects.filter(
                    hashtag=InternHashtag.TASK_VERIFIED_HASHTAG.value
                ).first()
                if task_list:
                    KarmaActivityLog.objects.create(
                        id=str(uuid.uuid4()),
                        user_id=intern_user_id,
                        task=task_list,
                        karma=karma_awarded,
                        appraiser_approved=True,
                        updated_by_id=admin_id,
                        updated_at=now(),
                        created_by_id=admin_id,
                        created_at=now()
                    )
                    wallet, _ = Wallet.objects.get_or_create(
                        user_id=intern_user_id,
                        defaults={'created_by_id': admin_id, 'updated_by_id': admin_id}
                    )
                    Wallet.objects.filter(id=wallet.id).update(karma=F('karma') + karma_awarded)

            from db.mentor import SystemActionLog
            SystemActionLog.objects.create(
                action_type=SystemActionLog.ActionType.INTERN_TASK_UPDATE.value,
                actor_user_id=admin_id,
                subject_user_id=intern_user_id,
                entity_name='intern_task',
                entity_id=task.id,
                old_data={"is_verified": False, "karma_awarded": 0},
                new_data={"is_verified": True, "karma_awarded": karma_awarded, "verified_by": admin_id}
            )

        return CustomResponse(general_message="Task verified successfully.").get_success_response()
