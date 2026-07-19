from rest_framework.views import APIView
from django.db.models import Q, Value, IntegerField
from django.db.models.functions import Coalesce
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.user import User
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from . import mulearner_serializers
from .company_views import _get_company_for_user

class CompanyMulearnerDirectoryAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Directory of MuLearners available to companies (creator or company mentor).",
        parameters=[
            OpenApiParameter("min_karma", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("max_karma", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("level", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("college", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("department", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("graduation_year", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("ig", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("skill", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("achievement", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("task", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: mulearner_serializers.MulearnerDirectorySerializer(many=True)},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not _get_company_for_user(user_id):
            return CustomResponse(
                general_message="Access denied. Verified company profile required."
            ).get_failure_response(status_code=403)
        users = User.objects.filter(
            user_settings_user__is_public=True
        ).select_related(
            "wallet_user",
            "user_lvl_link_user__level",
        ).prefetch_related(
            "user_organization_link_user__org",
            "user_organization_link_user__department",
        ).annotate(
            annotated_karma=Coalesce(
                "wallet_user__karma", Value(0), output_field=IntegerField()
            )
        )
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

        if min_karma:
            users = users.filter(annotated_karma__gte=int(min_karma))
        if max_karma:
            users = users.filter(annotated_karma__lte=int(max_karma))
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

        users = users.distinct()

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
