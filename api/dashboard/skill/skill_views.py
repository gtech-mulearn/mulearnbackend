import uuid
from datetime import datetime

from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404

from db.skill import Skill, TaskSkillLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType

from .skill_serializer import (
    SkillSerializer,
    SkillDropdownSerializer,
    SkillCreateSerializer,
    SkillUpdateSerializer,
)


class SkillListAPI(APIView):
    """List all skills with pagination and search"""
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Unauthorized"
            ).get_failure_response()

        # Get query params
        search = request.query_params.get('search', '')
        per_page = int(request.query_params.get('perPage', 10))
        page = int(request.query_params.get('pageIndex', 1))
        sort_by = request.query_params.get('sortBy', 'name') or 'name'
        is_asc = request.query_params.get('isAsc', 'true').lower() == 'true'
        active_only = request.query_params.get('activeOnly', 'false').lower() == 'true'

        # Base query
        skills = Skill.objects.all()
        
        if active_only:
            skills = skills.filter(is_active=True)

        if search:
            skills = skills.filter(name__icontains=search)

        # Count total before pagination
        total_count = skills.count()

        # Sorting
        order_prefix = '' if is_asc else '-'
        skills = skills.order_by(f'{order_prefix}{sort_by}')

        # Pagination
        start = (page - 1) * per_page
        end = start + per_page
        skills = skills[start:end]

        serializer = SkillSerializer(skills, many=True)

        return CustomResponse(
            response={
                "skills": serializer.data,
                "pagination": {
                    "totalRecords": total_count,
                    "currentPage": page,
                    "perPage": per_page,
                    "totalPages": (total_count + per_page - 1) // per_page,
                }
            }
        ).get_success_response()


class SkillDropdownAPI(APIView):
    """Get skills for dropdown selection"""
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Unauthorized"
            ).get_failure_response()

        skills = Skill.objects.filter(is_active=True).order_by('name')
        serializer = SkillDropdownSerializer(skills, many=True)
        
        return CustomResponse(response=serializer.data).get_success_response()


class SkillCreateAPI(APIView):
    """Create a new skill"""
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Unauthorized"
            ).get_failure_response()

        serializer = SkillCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                general_message="Validation error",
                response=serializer.errors
            ).get_failure_response()

        data = serializer.validated_data

        # Check for duplicate name or code
        if Skill.objects.filter(name=data['name']).exists():
            return CustomResponse(
                general_message=f"Skill with name '{data['name']}' already exists"
            ).get_failure_response()

        if Skill.objects.filter(code=data['code']).exists():
            return CustomResponse(
                general_message=f"Skill with code '{data['code']}' already exists"
            ).get_failure_response()

        skill = Skill.objects.create(
            id=str(uuid.uuid4()),
            name=data['name'],
            code=data['code'].upper(),
            description=data.get('description', ''),
            icon=data.get('icon', ''),
            is_active=data.get('is_active', True),
            created_by_id=user_id,
            updated_by_id=user_id,
        )

        return CustomResponse(
            general_message="Skill created successfully",
            response=SkillSerializer(skill).data
        ).get_success_response()


class SkillDetailAPI(APIView):
    """Get, update, or delete a specific skill"""
    authentication_classes = [CustomizePermission]

    def get(self, request, skill_id):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Unauthorized"
            ).get_failure_response()

        skill = get_object_or_404(Skill, id=skill_id)
        serializer = SkillSerializer(skill)
        
        # Get task count for this skill
        task_count = TaskSkillLink.objects.filter(skill_id=skill_id).count()
        
        response_data = serializer.data
        response_data['task_count'] = task_count
        
        return CustomResponse(response=response_data).get_success_response()

    @role_required([RoleType.ADMIN.value])
    def put(self, request, skill_id):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Unauthorized"
            ).get_failure_response()

        skill = get_object_or_404(Skill, id=skill_id)
        serializer = SkillUpdateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return CustomResponse(
                general_message="Validation error",
                response=serializer.errors
            ).get_failure_response()

        data = serializer.validated_data

        # Check for duplicate name (excluding current skill)
        if 'name' in data and data['name'] != skill.name:
            if Skill.objects.filter(name=data['name']).exclude(id=skill_id).exists():
                return CustomResponse(
                    general_message=f"Skill with name '{data['name']}' already exists"
                ).get_failure_response()

        # Check for duplicate code (excluding current skill)
        if 'code' in data and data['code'] != skill.code:
            if Skill.objects.filter(code=data['code']).exclude(id=skill_id).exists():
                return CustomResponse(
                    general_message=f"Skill with code '{data['code']}' already exists"
                ).get_failure_response()

        # Update fields
        if 'name' in data:
            skill.name = data['name']
        if 'code' in data:
            skill.code = data['code'].upper()
        if 'description' in data:
            skill.description = data['description']
        if 'icon' in data:
            skill.icon = data['icon']
        if 'is_active' in data:
            skill.is_active = data['is_active']

        skill.updated_by_id = user_id
        skill.save()

        return CustomResponse(
            general_message="Skill updated successfully",
            response=SkillSerializer(skill).data
        ).get_success_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, skill_id):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Unauthorized"
            ).get_failure_response()

        skill = get_object_or_404(Skill, id=skill_id)
        
        # Check if skill has linked tasks
        task_count = TaskSkillLink.objects.filter(skill_id=skill_id).count()
        if task_count > 0:
            return CustomResponse(
                general_message=f"Cannot delete skill. It is linked to {task_count} task(s). Remove the links first or deactivate the skill."
            ).get_failure_response()

        skill_name = skill.name
        skill.delete()

        return CustomResponse(
            general_message=f"Skill '{skill_name}' deleted successfully"
        ).get_success_response()


class SkillTasksAPI(APIView):
    """Get all tasks linked to a specific skill"""
    authentication_classes = [CustomizePermission]

    def get(self, request, skill_id):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Unauthorized"
            ).get_failure_response()

        skill = get_object_or_404(Skill, id=skill_id)
        
        # Get all tasks linked to this skill
        task_links = TaskSkillLink.objects.filter(
            skill_id=skill_id
        ).select_related('task')

        tasks = []
        for link in task_links:
            tasks.append({
                'id': link.task.id,
                'title': link.task.title,
                'hashtag': link.task.hashtag,
                'karma': link.task.karma,
                'active': link.task.active,
            })

        return CustomResponse(
            response={
                'skill': SkillSerializer(skill).data,
                'tasks': tasks,
                'task_count': len(tasks)
            }
        ).get_success_response()
