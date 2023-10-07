from django.db.models import Count, Q, F, Case, When, Value
from rest_framework.views import APIView

from db.task import Level, Wallet
from db.user import User
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils, DateTimeUtils

from . import serializers
from .dash_campus_helper import get_user_college_link


class CampusDetailsAPI(APIView):
    """
    Campus Details API

    This API view allows authorized users with specific roles (Campus Lead or Enabler)
    to access details about their campus

    Attributes:
        authentication_classes (list): A list containing the CustomizePermission class for authentication.

    Method:
        get(request): Handles GET requests to retrieve campus details for the authenticated user.
    """
    authentication_classes = [CustomizePermission]

    # Use the role_required decorator to specify the allowed roles for this view
    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.ENABLER.value])
    def get(self, request):
        # Fetch the user's ID from the request using JWTUtils
        user_id = JWTUtils.fetch_user_id(request)

        # Get the user's organization link using the user ID
        user_org_link = get_user_college_link(user_id)

        # Check if the user's organization link is None
        if user_org_link.org is None:
            # If it is None, return a failure response with a specific message
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        # Serialize the user's organization link using the CampusDetailsSerializer
        serializer = serializers.CampusDetailsSerializer(user_org_link, many=False)

        # Return a success response with the serialized data
        return CustomResponse(response=serializer.data).get_success_response()


class CampusStudentInEachLevelAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.ENABLER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = get_user_college_link(user_id)

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        level_with_student_count = Level.objects.annotate(
            students=Count(
                "user_lvl_link_level__user",
                filter=Q(
                    user_lvl_link_level__user__user_organization_link_user__org=user_org_link.org
                ),
            )
        ).values(level=F("level_order"), students=F("students"))

        return CustomResponse(response=level_with_student_count).get_success_response()


class CampusStudentDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.ENABLER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = get_user_college_link(user_id)

        start_date, end_date = DateTimeUtils.get_start_and_end_of_previous_month()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        rank = (
            Wallet.objects.filter(
                user__user_organization_link_user__org=user_org_link.org,
                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .distinct('user_id')
            .order_by("-karma", "-created_at")
            .values(
                "user_id",
                "karma",
            )
        )

        ranks = {user["user_id"]: i + 1 for i, user in enumerate(rank)}

        user_org_links = (
            User.objects.filter(
                user_organization_link_user__org=user_org_link.org,
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .distinct('id')
            .annotate(
                user_id=F("id"),
                muid=F("mu_id"),
                karma=F("wallet_user__karma"),
                level=F("user_lvl_link_user__level__name"),
                join_date=F("created_at"),
            )
            .annotate(
                is_active=Case(
                    When(
                        Q(
                            karma_activity_log_user__created_at__range=(
                                start_date,
                                end_date)),
                        then=Value("Active")),
                    default=Value("Not Active")
                    )
            ))
        paginated_queryset = CommonUtils.get_paginated_queryset(
            user_org_links,
            request,
            ["first_name", "last_name", "level"],
            {
                "first_name": "first_name",
                "last_name": "last_name",
                "muid": "mu_id",
                "karma": "wallet_user__karma",
                "level": "user_lvl_link_user__level__level_order",
                "is_active": "karma_activity_log_user__created_at",
                "joined_at": "created_at"
            },
        )

        serializer = serializers.CampusStudentDetailsSerializer(
            paginated_queryset.get("queryset"), many=True, context={"ranks": ranks}
        )

        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class CampusStudentDetailsCSVAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.ENABLER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = get_user_college_link(user_id)

        start_date, end_date = DateTimeUtils.get_start_and_end_of_previous_month()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        rank = (
            Wallet.objects.filter(
                user__user_organization_link_user__org=user_org_link.org,
                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .distinct()
            .order_by("-karma", "-created_at")
            .values(
                "user_id",
                "karma",
            )
        )

        ranks = {user["user_id"]: i + 1 for i, user in enumerate(rank)}

        user_org_links = (
            User.objects.filter(
                user_organization_link_user__org=user_org_link.org,
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .distinct()
            .annotate(
                user_id=F("id"),
                muid=F("mu_id"),
                karma=F("wallet_user__karma"),
                level=F("user_lvl_link_user__level__name"),
                join_date=F("created_at"),
            )
            .annotate(
                is_active=Case(
                    When(
                        Q(
                            karma_activity_log_user__created_at__range=(
                                start_date,
                                end_date)),
                        then=Value("Active")),
                    default=Value("Not Active")
                )
            ))

        serializer = serializers.CampusStudentDetailsSerializer(
            user_org_links, many=True, context={"ranks": ranks}
        )
        return CommonUtils.generate_csv(serializer.data, "Campus Student Details")


class WeeklyKarmaAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.ENABLER.value])
    def get(self, request):
        try:
            user_id = JWTUtils.fetch_user_id(request)

            user_org_link = get_user_college_link(user_id)

            if user_org_link.org is None:
                return CustomResponse(
                    general_message="Campus lead has no college"
                ).get_failure_response()

            serializer = serializers.WeeklyKarmaSerializer(user_org_link)
            return CustomResponse(response=serializer.data).get_success_response()
        except Exception as e:
            return CustomResponse(response=str(e)).get_failure_response()
