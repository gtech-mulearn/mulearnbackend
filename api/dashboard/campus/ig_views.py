from rest_framework.views import APIView
from rest_framework import status
from utils.response import CustomResponse
from utils.permission import CustomizePermission, role_required
from utils.types import RoleType
from utils.utils import CommonUtils
from .dash_campus_helper import get_campus_context
from api.dashboard.ig import services as ig_services
from . import serializers

class CampusIGsAPI(APIView):
    authentication_classes = [CustomizePermission]
    
    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request):
        org, error = get_campus_context(request)
        if error: return error
        
        qs = ig_services.get_campus_igs(org.id)
        paginated = CommonUtils.get_paginated_queryset(
            qs, request, 
            search_fields=['name', 'code'], 
            sort_fields={'name': 'name', 'member_count': 'campus_member_count'}
        )
        serializer = serializers.CampusIGListSerializer(paginated.get('queryset'), many=True)
        return CustomResponse(
            response={"data": serializer.data, "pagination": paginated.get("pagination")}
        ).get_success_response()

class CampusIGMembersAPI(APIView):
    authentication_classes = [CustomizePermission]
    
    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request, ig_id):
        org, error = get_campus_context(request)
        if error: return error
        
        qs = ig_services.get_ig_members(ig_id, org.id)
        paginated = CommonUtils.get_paginated_queryset(
            qs, request, 
            search_fields=['user__full_name', 'user__muid'], 
            sort_fields={'full_name': 'user__full_name', 'karma': 'user__wallet_user__karma'}
        )
        serializer = serializers.CampusIGMemberSerializer(paginated.get('queryset'), many=True)
        return CustomResponse(
            response={"data": serializer.data, "pagination": paginated.get("pagination")}
        ).get_success_response()
