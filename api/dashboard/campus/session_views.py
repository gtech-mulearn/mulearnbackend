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

class CampusMentorSessionCreateAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Campus Sessions'],
        description="Create a new mentorship session for the campus.",
        request=mentor_serializers.SessionCreateSerializer,
        responses={200: mentor_serializers.SessionCreateSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        
        # Verify the user is an approved Campus Mentor
        active_assignments = UserMentor.objects.filter(
            user_id=user_id, 
            status=UserMentor.Status.APPROVED, 
            mentor_tier=UserMentor.MentorTier.CAMPUS_MENTOR
        )

        if not active_assignments.exists():
            return CustomResponse(
                general_message="You are not an approved Campus Mentor."
            ).get_failure_response(status_code=403)

        data = request.data.copy()
        
        org_id = request.data.get("org_id")
        if not org_id:
            if active_assignments.count() > 1:
                 return CustomResponse(
                     general_message="You are assigned to multiple campuses. Please specify the org_id."
                 ).get_failure_response(status_code=400)
            org_id = active_assignments.first().org_id

        if not active_assignments.filter(org_id=org_id).exists():
             return CustomResponse(
                 general_message="You are not assigned as a Campus Mentor for this organization."
             ).get_failure_response(status_code=403)

        data["entity_id"] = str(org_id)
        data["session_type"] = MentorshipSession.SessionType.CAMPUS_SESSION

        serializer = mentor_serializers.SessionCreateSerializer(
            data=data, context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Campus session created successfully and is pending approval.",
                response=serializer.data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

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
        student_org_id = user_org_link.org_id if user_org_link else None
        
        mentor_org_ids = UserMentor.objects.filter(
            user_id=user_id,
            status=UserMentor.Status.APPROVED,
            mentor_tier=UserMentor.MentorTier.CAMPUS_MENTOR
        ).values_list("org_id", flat=True)
        
        all_allowed_org_ids = set()
        if student_org_id:
            all_allowed_org_ids.add(student_org_id)
        all_allowed_org_ids.update(mentor_org_ids)

        if not all_allowed_org_ids:
            return CustomResponse(
                general_message="You are not associated with any campus."
            ).get_failure_response(status_code=404)

        from django.db.models import Q
        sessions = MentorshipSession.objects.filter(
            entity_id__in=all_allowed_org_ids, 
            session_type=MentorshipSession.SessionType.CAMPUS_SESSION,
            is_deleted=False
        ).select_related("created_by")

        roles = JWTUtils.fetch_role(request)
        is_global_elevated = any(
            role in roles
            for role in [
                RoleType.ADMIN.value,
                RoleType.CAMPUS_LEAD.value,
                RoleType.LEAD_ENABLER.value,
            ]
        )

        status_filter = request.query_params.get("status")
        
        if is_global_elevated:
            if status_filter:
                sessions = sessions.filter(status=status_filter)
        else:
            if status_filter:
                # If they filter by a status other than SCHEDULED, they won't see student org sessions
                student_q = Q(entity_id=student_org_id, status=MentorshipSession.Status.SCHEDULED) if status_filter == MentorshipSession.Status.SCHEDULED else Q(pk__isnull=True)
                sessions = sessions.filter(
                    Q(entity_id__in=mentor_org_ids, status=status_filter) | student_q
                )
            else:
                sessions = sessions.filter(
                    Q(entity_id__in=mentor_org_ids) |
                    Q(entity_id=student_org_id, status=MentorshipSession.Status.SCHEDULED)
                )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            sessions, request, 
            search_fields=["title", "description"],
            sort_fields={"created_at": "created_at", "starts_at": "starts_at"}
        )
        
        qs = paginated_queryset.get("queryset")
        org_ids = [s.entity_id for s in qs if s.session_type in (MentorshipSession.SessionType.CAMPUS_SESSION, MentorshipSession.SessionType.COMPANY_SESSION)]
        from db.organization import Organization
        org_map = dict(Organization.objects.filter(id__in=org_ids).values_list('id', 'title'))
        
        serializer = mentor_serializers.SessionListSerializer(
            qs, many=True, context={"ig_map": {}, "org_map": org_map}
        )
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()
