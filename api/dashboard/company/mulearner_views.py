from rest_framework.views import APIView
from django.db.models import Q
from utils.permission import CustomizePermission, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.user import User
from . import mulearner_serializers

class CompanyMulearnerDirectoryAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.COMPANY.value])
    def get(self, request):
        # 1. Base query: Only users with public profile
        users = User.objects.filter(user_settings_user__is_public=True)

        # 2. Extract Query Params
        min_karma = request.query_params.get('min_karma')
        max_karma = request.query_params.get('max_karma')
        level = request.query_params.get('level')
        college = request.query_params.get('college')
        department = request.query_params.get('department')
        graduation_year = request.query_params.get('graduation_year')
        ig = request.query_params.get('ig')
        skill = request.query_params.get('skill')
        achievement = request.query_params.get('achievement')
        task = request.query_params.get('task')

        # 3. Apply Relational Filters
        if min_karma:
            users = users.filter(wallet_user__karma__gte=min_karma)
        if max_karma:
            users = users.filter(wallet_user__karma__lte=max_karma)
        if level:
            users = users.filter(user_lvl_link_user__level__level_order=level)
        if college:
            users = users.filter(
                user_organization_link_user__org__title__icontains=college, 
                user_organization_link_user__org__org_type='College'
            )
        if department:
            users = users.filter(user_organization_link_user__department__title__icontains=department)
        if graduation_year:
            users = users.filter(user_organization_link_user__graduation_year=graduation_year)
        if ig:
            users = users.filter(user_ig_link_user__ig__name__icontains=ig)
        if skill:
            users = users.filter(skill_progress__skill_id=skill)
        if achievement:
            users = users.filter(achievements__achievement_id=achievement)
        if task:
            users = users.filter(karma_activity_log_user__task_id=task)

        # Avoid duplicates due to joins
        users = users.distinct()

        # 4. Standard Search & Pagination
        paginated_queryset = CommonUtils.get_paginated_queryset(
            users, request, 
            search_fields=["full_name", "muid", "email"],
            sort_fields={"full_name": "full_name", "created_at": "created_at", "karma": "wallet_user__karma"}
        )
        
        serializer = mulearner_serializers.MulearnerDirectorySerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()
