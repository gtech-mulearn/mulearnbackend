from rest_framework.views import APIView
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.mentor import MentorshipSession
from db.user import UserMentor
from api.dashboard.mentor import serializers as mentor_serializers
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from .dash_campus_helper import get_user_college_link

# sessions are Interest-Group-scoped
# only, and campus mentors do not create sessions. (The list endpoint remains for
# viewing any legacy campus sessions.)


class CampusSessionListAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Campus Sessions'],
        description="List campus mentorship sessions. Admins, campus leads, enablers, and approved campus mentors see all statuses; other users see only scheduled sessions.",
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: mentor_serializers.SessionListSerializer(many=True)},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        
        user_org_link = get_user_college_link(user_id)
        if not user_org_link:
            return CustomResponse(
                general_message="You are not associated with any campus."
            ).get_failure_response(status_code=404)

        sessions = MentorshipSession.objects.filter(
            entity_id=user_org_link.org_id, 
            session_type=MentorshipSession.SessionType.CAMPUS_SESSION,
            is_deleted=False
        )

        roles = JWTUtils.fetch_role(request)
        is_elevated = any(
            role in roles
            for role in [
                RoleType.ADMIN.value,
                RoleType.CAMPUS_LEAD.value,
                RoleType.LEAD_ENABLER.value,
            ]
        )
        if not is_elevated:
            is_elevated = UserMentor.objects.filter(
                user_id=user_id,
                status=UserMentor.Status.APPROVED,
                mentor_tier=UserMentor.MentorTier.CAMPUS_MENTOR,
                org_id=user_org_link.org_id,
            ).exists()

        if is_elevated:
            status = request.query_params.get("status")
            if status:
                sessions = sessions.filter(status=status)
        else:
            # Regular students can only see scheduled sessions
            sessions = sessions.filter(status=MentorshipSession.Status.SCHEDULED)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            sessions, request, 
            search_fields=["title", "description"],
            sort_fields={"created_at": "created_at", "starts_at": "starts_at"}
        )
        
        serializer = mentor_serializers.SessionListSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()
