import uuid

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework import status
from utils.response import CustomResponse
from utils.permission import CustomizePermission, JWTUtils
from utils.types import RoleType, OrganizationType
from utils.utils import CommonUtils, DateTimeUtils
from .dash_campus_helper import get_campus_context, campus_staff_required
from api.dashboard.ig import services as ig_services
from . import serializers
from drf_spectacular.utils import extend_schema

from db.campus import CampusIGChapter
from db.task import UserIgLink
from db.organization import UserOrganizationLink


class CampusIGsAPI(APIView):
    authentication_classes = [CustomizePermission]
    
    @campus_staff_required
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Retrieve Campus I Gs.",
        responses={200: serializers.CampusIGListSerializer},
    )
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
    
    @campus_staff_required
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Retrieve Campus I G Members.",
        responses={200: serializers.CampusIGMemberSerializer},
    )
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


class CampusIGChapterJoinAPI(APIView):
    """
    POST /api/v1/dashboard/campus/ig-chapters/<chapter_id>/join/

    Allows an authenticated user to join a Campus IG Chapter.
    The user must have a verified college organization link to the same
    campus organization that hosts the chapter.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Campus'],
        description=(
            "Join a Campus IG Chapter. The authenticated user must be a verified "
            "member of the same campus organization that hosts this chapter."
        ),
        responses={200: None},
    )
    def post(self, request, chapter_id):
        user_id = JWTUtils.fetch_user_id(request)

        # Step 1: Validate the chapter exists and is active
        chapter = CampusIGChapter.objects.filter(id=chapter_id, is_active=True).first()
        if not chapter:
            return CustomResponse(
                general_message="Campus IG Chapter not found or inactive"
            ).get_failure_response()

        # Step 2: Validate the user has a verified college org link
        user_org_link = UserOrganizationLink.objects.filter(
            user_id=user_id,
            org__org_type=OrganizationType.COLLEGE.value,
            verified=True,
        ).first()
        if not user_org_link:
            return CustomResponse(
                general_message="You must be a verified college member to join a Campus IG Chapter"
            ).get_failure_response()

        # Step 3: Validate the user belongs to the same campus as the chapter
        if str(user_org_link.org_id) != str(chapter.org_id):
            return CustomResponse(
                general_message="You can only join an IG Chapter from your own campus"
            ).get_failure_response()

        # Step 4: Handle existing UserIgLink for this IG
        existing_link = UserIgLink.objects.filter(
            user_id=user_id,
            ig=chapter.ig,
            assignment_type=UserIgLink.AssignmentType.LEARNER,
        ).first()

        if existing_link:
            if existing_link.is_active:
                return CustomResponse(
                    general_message="You are already a member of this Interest Group"
                ).get_failure_response()
            # Reactivate an existing inactive link
            existing_link.is_active = True
            existing_link.unassigned_at = None
            existing_link.assigned_by_id = user_id
            existing_link.save(update_fields=["is_active", "unassigned_at", "assigned_by"])
        else:
            # Create a new learner link
            UserIgLink.objects.create(
                id=uuid.uuid4(),
                user_id=user_id,
                ig=chapter.ig,
                assignment_type=UserIgLink.AssignmentType.LEARNER,
                is_active=True,
                assigned_by_id=user_id,
                created_by_id=user_id,
            )

        return CustomResponse(
            general_message="Successfully joined the Campus IG Chapter"
        ).get_success_response()


class CampusIGChapterLeaveAPI(APIView):
    """
    DELETE /api/v1/dashboard/campus/ig-chapters/<chapter_id>/leave/

    Allows an authenticated user to leave a Campus IG Chapter.
    The user must be a verified member of the same campus organization.
    The UserIgLink is deactivated (soft-delete) to preserve history.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Campus'],
        description=(
            "Leave a Campus IG Chapter. The authenticated user's active learner "
            "link to the Interest Group is deactivated. History is preserved."
        ),
        responses={200: None},
    )
    def delete(self, request, chapter_id):
        user_id = JWTUtils.fetch_user_id(request)

        # Step 1: Validate the chapter exists
        chapter = CampusIGChapter.objects.filter(id=chapter_id).first()
        if not chapter:
            return CustomResponse(
                general_message="Campus IG Chapter not found"
            ).get_failure_response()

        # Step 2: Validate the user belongs to the same campus as the chapter
        user_org_link = UserOrganizationLink.objects.filter(
            user_id=user_id,
            org__org_type=OrganizationType.COLLEGE.value,
            verified=True,
        ).first()
        if not user_org_link or str(user_org_link.org_id) != str(chapter.org_id):
            return CustomResponse(
                general_message="You can only leave an IG Chapter from your own campus"
            ).get_failure_response()

        # Step 3: Find the active learner link for this IG
        link = UserIgLink.objects.filter(
            user_id=user_id,
            ig=chapter.ig,
            assignment_type=UserIgLink.AssignmentType.LEARNER,
            is_active=True,
        ).first()
        if not link:
            return CustomResponse(
                general_message="You are not an active member of this Interest Group"
            ).get_failure_response()

        # Step 4: Soft-deactivate the link
        link.is_active = False
        link.unassigned_at = DateTimeUtils.get_current_utc_time()
        link.save(update_fields=["is_active", "unassigned_at"])

        return CustomResponse(
            general_message="Successfully left the Campus IG Chapter"
        ).get_success_response()
