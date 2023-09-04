from django.db.models import Count, Q, F
from rest_framework.views import APIView

from db.organization import UserOrganizationLink
from db.task import Level, TotalKarma
from db.user import User
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils

from . import serializers
from .dash_campus_helper import get_user_college_link


class CampusDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.ENABLER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = get_user_college_link(user_id)

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        serializer = serializers.CampusDetailsSerializer(user_org_link, many=False)

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

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        rank = (
            TotalKarma.objects.filter(
                user__user_organization_link_user__org=user_org_link.org,
                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .distinct()
            .order_by("-karma")
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
                karma=F("total_karma_user__karma"),
                level=F("user_lvl_link_user__level__name"),
                join_date=F("created_at"),
            )
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            user_org_links,
            request,
            ["first_name", "last_name", "level"],
            {
                "first_name": "first_name",
                "last_name": "last_name",
                "muid": "mu_id",
                "karma": "total_karma_user__karma",
                "level": "user_lvl_link_user__level__level_order",
                "joined_at" : "created_at"
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

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        rank = (
            TotalKarma.objects.filter(
                user__user_organization_link_user__org=user_org_link.org,
                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .distinct()
            .order_by("-karma")
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
                karma=F("total_karma_user__karma"),
                level=F("user_lvl_link_user__level__name"),
                join_date=F("created_at"),
            )
        )

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
