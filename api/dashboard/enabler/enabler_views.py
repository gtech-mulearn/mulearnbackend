from rest_framework.views import APIView
from django.db.models import Count, Sum
from db.organization import Organization, UserOrganizationLink, EnablerCampusNote
from db.user import UserRoleLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils
from . import serializers
from drf_spectacular.utils import extend_schema
from utils.schema_utils import CustomResponseSerializer

class EnablerHomeSummaryAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ENABLER.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(tags=['Dashboard - Enabler'], description="Retrieve Enabler Home Summary.",
        responses={200: CustomResponseSerializer},
    )
    def get(self, request):
        enabler_id = JWTUtils.fetch_user_id(request)
        
        assigned_campuses = UserOrganizationLink.objects.filter(
            user_id=enabler_id,
            org__org_type=OrganizationType.COLLEGE.value
        ).values_list('org_id', flat=True)

        total_campuses = assigned_campuses.count()
        total_students = 0 # Placeholder for actual aggregation if needed
        total_karma = 0    # Placeholder for actual aggregation if needed

        return CustomResponse(response={
            "total_campuses": total_campuses,
            "total_students": total_students,
            "total_karma": total_karma
        }).get_success_response()

class EnablerCampusListAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ENABLER.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(
        tags=['Dashboard - Enabler'],
        description="Retrieve Enabler Campus List.",
        responses={200: serializers.EnablerCampusListSerializer},
    )
    def get(self, request):
        enabler_id = JWTUtils.fetch_user_id(request)
        
        assigned_campuses_ids = UserOrganizationLink.objects.filter(
            user_id=enabler_id,
            org__org_type=OrganizationType.COLLEGE.value
        ).values_list('org_id', flat=True)

        campuses = Organization.objects.filter(id__in=assigned_campuses_ids)
        paginated_queryset = CommonUtils.get_paginated_queryset(campuses, request, ["title", "code"])
        
        serializer = serializers.EnablerCampusListSerializer(paginated_queryset.get('queryset'), many=True)
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get('pagination')
        )

class EnablerCampusReviewAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ENABLER.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(
        tags=['Dashboard - Enabler'],
        description="Retrieve Enabler Campus Review.",
        responses={200: serializers.EnablerCampusListSerializer},
    )
    def get(self, request, campus_id):
        enabler_id = JWTUtils.fetch_user_id(request)
        
        is_assigned = UserOrganizationLink.objects.filter(
            user_id=enabler_id,
            org_id=campus_id
        ).exists()

        if not is_assigned:
            return CustomResponse(general_message="Not assigned to this campus").get_failure_response()

        try:
            campus = Organization.objects.get(id=campus_id)
            serializer = serializers.EnablerCampusListSerializer(campus)
            return CustomResponse(response=serializer.data).get_success_response()
        except Organization.DoesNotExist:
            return CustomResponse(general_message="Campus not found").get_failure_response()

class EnablerCampusNoteAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ENABLER.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(
        tags=['Dashboard - Enabler'],
        description="Retrieve Enabler Campus Note.",
        responses={200: serializers.EnablerCampusNoteSerializer},
    )
    def get(self, request, campus_id):
        enabler_id = JWTUtils.fetch_user_id(request)
        
        notes = EnablerCampusNote.objects.filter(
            campus_id=campus_id,
            enabler_id=enabler_id
        ).order_by('-created_at')

        paginated_queryset = CommonUtils.get_paginated_queryset(notes, request, ["note"])
        serializer = serializers.EnablerCampusNoteSerializer(paginated_queryset.get('queryset'), many=True)
        
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get('pagination')
        )

    @role_required([RoleType.ENABLER.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(
        tags=['Dashboard - Enabler'],
        description="Create Enabler Campus Note.",
        request=serializers.EnablerCampusNoteSerializer,
        responses={200: serializers.EnablerCampusNoteSerializer},
    )
    def post(self, request, campus_id):
        enabler_id = JWTUtils.fetch_user_id(request)
        
        is_assigned = UserOrganizationLink.objects.filter(
            user_id=enabler_id,
            org_id=campus_id
        ).exists()

        if not is_assigned:
            return CustomResponse(general_message="Not assigned to this campus").get_failure_response()

        serializer = serializers.EnablerCampusNoteSerializer(
            data=request.data,
            context={"enabler_id": enabler_id, "campus_id": campus_id}
        )

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message="Note added successfully").get_success_response()
            
        return CustomResponse(response=serializer.errors).get_failure_response()

class EnablerReportsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ENABLER.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(tags=['Dashboard - Enabler'], description="Retrieve Enabler Reports.",
        responses={200: CustomResponseSerializer},
    )
    def get(self, request):
        enabler_id = JWTUtils.fetch_user_id(request)
        
        assigned_campuses_ids = UserOrganizationLink.objects.filter(
            user_id=enabler_id,
            org__org_type=OrganizationType.COLLEGE.value
        ).values_list('org_id', flat=True)

        assigned_campuses_count = assigned_campuses_ids.count()

        campuses_data = []
        for campus_id in assigned_campuses_ids:
            campus = Organization.objects.get(id=campus_id)
            campuses_data.append({
                "campus_id": campus.id,
                "campus_name": campus.title,
                "health_score": 72, # Mocked health score
                "karma_last_30_days": 4800, # Mocked karma
                "events_last_30_days": 2, # Mocked events
                "followups_pending": EnablerCampusNote.objects.filter(campus_id=campus_id, status='open').count()
            })

        followups_closed = EnablerCampusNote.objects.filter(campus_id__in=assigned_campuses_ids, status='closed').count()
        followups_pending = EnablerCampusNote.objects.filter(campus_id__in=assigned_campuses_ids, status='open').count()

        return CustomResponse(response={
            "period": "30d",
            "summary": {
                "assigned_campuses": assigned_campuses_count,
                "active_campuses": assigned_campuses_count,
                "at_risk_campuses": 0,
                "followups_closed": followups_closed,
                "followups_pending": followups_pending
            },
            "campuses": campuses_data
        }).get_success_response()
