from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s
from rest_framework.views import APIView

from db.organization import Organization, UserOrganizationLink, EnablerCampusNote
from db.task import KarmaActivityLog, Wallet
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils
from . import serializers


class EnablerHomeSummaryAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ENABLER.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(tags=['Dashboard - Enabler'], description="Retrieve Enabler Home Summary.",
        responses={200: inline_serializer(
            name='EnablerHomeSummaryResponse',
            fields={
                'total_campuses': s.IntegerField(),
                'total_students': s.IntegerField(),
                'total_karma': s.IntegerField(),
            },
        )},
    )
    def get(self, request):
        enabler_id = JWTUtils.fetch_user_id(request)

        # FIX: Add .distinct() to prevent duplicate campus IDs from corrupting aggregations
        assigned_campus_ids = UserOrganizationLink.objects.filter(
            user_id=enabler_id,
            org__org_type=OrganizationType.COLLEGE.value
        ).values_list('org_id', flat=True).distinct()

        total_campuses = assigned_campus_ids.count()

        # FIX: Implement real student count — students are users linked to the assigned campuses
        total_students = UserOrganizationLink.objects.filter(
            org_id__in=assigned_campus_ids,
            org__org_type=OrganizationType.COLLEGE.value
        ).exclude(user_id=enabler_id).values('user_id').distinct().count()

        # FIX: Implement real total karma — sum karma from Wallet for all students in those campuses
        total_karma = Wallet.objects.filter(
            user__user_organization_link_user__org_id__in=assigned_campus_ids
        ).aggregate(total=Sum('karma'))['total'] or 0

        return CustomResponse(response={
            "total_campuses": total_campuses,
            "total_students": total_students,
            "total_karma": total_karma,
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

        # FIX: Add .distinct() to avoid showing duplicate campuses if UserOrganizationLink has dups
        assigned_campuses_ids = UserOrganizationLink.objects.filter(
            user_id=enabler_id,
            org__org_type=OrganizationType.COLLEGE.value
        ).values_list('org_id', flat=True).distinct()

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

        # FIX: Also verify the campus is actually a COLLEGE type org
        is_assigned = UserOrganizationLink.objects.filter(
            user_id=enabler_id,
            org_id=campus_id,
            org__org_type=OrganizationType.COLLEGE.value
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

        # FIX: Also verify the campus is a COLLEGE type org
        is_assigned = UserOrganizationLink.objects.filter(
            user_id=enabler_id,
            org_id=campus_id,
            org__org_type=OrganizationType.COLLEGE.value
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

    # FIX: Add missing PATCH endpoint to allow enablers to update/close notes
    @role_required([RoleType.ENABLER.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(
        tags=['Dashboard - Enabler'],
        description="Update Enabler Campus Note (e.g., change status from open to closed).",
        request=serializers.EnablerCampusNoteUpdateSerializer,
        responses={200: serializers.EnablerCampusNoteSerializer},
    )
    def patch(self, request, campus_id):
        enabler_id = JWTUtils.fetch_user_id(request)
        note_id = request.data.get("note_id")

        if not note_id:
            return CustomResponse(general_message="note_id is required").get_failure_response()

        try:
            note = EnablerCampusNote.objects.get(
                id=note_id,
                campus_id=campus_id,
                enabler_id=enabler_id  # Ensures ownership — an enabler can only edit their own notes
            )
        except EnablerCampusNote.DoesNotExist:
            return CustomResponse(general_message="Note not found").get_failure_response()

        serializer = serializers.EnablerCampusNoteUpdateSerializer(
            note,
            data=request.data,
            partial=True,
            context={"enabler_id": enabler_id}
        )

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message="Note updated successfully").get_success_response()

        return CustomResponse(response=serializer.errors).get_failure_response()

    # FIX: Add missing DELETE endpoint for note removal
    @role_required([RoleType.ENABLER.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(
        tags=['Dashboard - Enabler'],
        description="Delete an Enabler Campus Note.",
        responses={200: inline_serializer(name='DeleteNoteResponse', fields={'message': s.CharField()})},
    )
    def delete(self, request, campus_id):
        enabler_id = JWTUtils.fetch_user_id(request)
        note_id = request.data.get("note_id")

        if not note_id:
            return CustomResponse(general_message="note_id is required").get_failure_response()

        try:
            note = EnablerCampusNote.objects.get(
                id=note_id,
                campus_id=campus_id,
                enabler_id=enabler_id  # Ensures ownership
            )
        except EnablerCampusNote.DoesNotExist:
            return CustomResponse(general_message="Note not found").get_failure_response()

        note.delete()
        return CustomResponse(general_message="Note deleted successfully").get_success_response()


class EnablerReportsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ENABLER.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(tags=['Dashboard - Enabler'], description="Retrieve Enabler Reports.",
        responses={200: inline_serializer(
            name='EnablerReportsResponse',
            fields={
                'period': s.CharField(),
                'summary': inline_serializer(
                    name='EnablerReportsSummary',
                    fields={
                        'assigned_campuses': s.IntegerField(),
                        'active_campuses': s.IntegerField(),
                        'at_risk_campuses': s.IntegerField(),
                        'followups_closed': s.IntegerField(),
                        'followups_pending': s.IntegerField(),
                    },
                ),
                'campuses': s.ListField(child=s.JSONField()),
            },
        )},
    )
    def get(self, request):
        enabler_id = JWTUtils.fetch_user_id(request)
        thirty_days_ago = timezone.now() - timedelta(days=30)

        # FIX: Add .distinct() to avoid duplicate campus IDs
        assigned_campuses_ids = UserOrganizationLink.objects.filter(
            user_id=enabler_id,
            org__org_type=OrganizationType.COLLEGE.value
        ).values_list('org_id', flat=True).distinct()

        assigned_campuses_count = assigned_campuses_ids.count()

        # FIX: Eliminate N+1 — fetch all campus data with annotated note counts in a single query
        campuses_qs = Organization.objects.filter(
            id__in=assigned_campuses_ids
        ).annotate(
            open_notes_count=Count(
                'enabler_campus_notes',
                filter=Q(
                    enabler_campus_notes__status='open',
                    enabler_campus_notes__enabler_id=enabler_id  # FIX: Consistent scoping to this enabler
                )
            )
        )

        campuses_data = []
        for campus in campuses_qs:
            campuses_data.append({
                "campus_id": campus.id,
                "campus_name": campus.title,
                "followups_pending": campus.open_notes_count,
            })

        # FIX: Consistent data visibility — scope follow-up counts to this enabler's notes only
        followups_closed = EnablerCampusNote.objects.filter(
            campus_id__in=assigned_campuses_ids,
            enabler_id=enabler_id,
            status='closed'
        ).count()

        followups_pending = EnablerCampusNote.objects.filter(
            campus_id__in=assigned_campuses_ids,
            enabler_id=enabler_id,
            status='open'
        ).count()

        return CustomResponse(response={
            "period": "30d",
            "summary": {
                "assigned_campuses": assigned_campuses_count,
                "active_campuses": assigned_campuses_count,
                "at_risk_campuses": 0,
                "followups_closed": followups_closed,
                "followups_pending": followups_pending,
            },
            "campuses": campuses_data,
        }).get_success_response()
