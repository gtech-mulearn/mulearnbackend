from rest_framework.views import APIView
from rest_framework import status
from utils.response import CustomResponse
from utils.permission import CustomizePermission, role_required
from utils.types import RoleType
from utils.utils import CommonUtils
from .dash_campus_helper import get_campus_context
from api.dashboard.learningcircle import services as lc_services
from . import serializers
from drf_spectacular.utils import extend_schema

class CampusLearningCirclesAPI(APIView):
    authentication_classes = [CustomizePermission]
    
    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Retrieve Campus Learning Circles.",
        responses={200: serializers.CampusLCListSerializer},
    )
    def get(self, request):
        org, error = get_campus_context(request)
        if error: return error
        
        qs = lc_services.get_campus_learning_circles(org.id)
        paginated = CommonUtils.get_paginated_queryset(
            qs, request, 
            search_fields=['title'], 
            sort_fields={'name': 'title', 'member_count': 'member_count'}
        )
        serializer = serializers.CampusLCListSerializer(paginated.get('queryset'), many=True)
        return CustomResponse(
            response={"data": serializer.data, "pagination": paginated.get("pagination")}
        ).get_success_response()

class CampusLCMembersAPI(APIView):
    authentication_classes = [CustomizePermission]
    
    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Retrieve Campus L C Members.",
        responses={200: serializers.CampusLCMemberSerializer},
    )
    def get(self, request, circle_id):
        org, error = get_campus_context(request)
        if error: return error
        
        qs = lc_services.get_lc_members(circle_id, org.id)
        paginated = CommonUtils.get_paginated_queryset(
            qs, request, 
            search_fields=['user__full_name', 'user__muid'], 
            sort_fields={'full_name': 'user__full_name', 'karma': 'user__wallet_user__karma'}
        )
        serializer = serializers.CampusLCMemberSerializer(paginated.get('queryset'), many=True)
        return CustomResponse(
            response={"data": serializer.data, "pagination": paginated.get("pagination")}
        ).get_success_response()
