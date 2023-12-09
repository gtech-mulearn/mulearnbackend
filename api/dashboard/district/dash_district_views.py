from itertools import islice

from django.db.models import Sum, F, Case, CharField, When
from rest_framework.views import APIView

from db.organization import UserOrganizationLink, Organization
from db.task import Level, Wallet
from db.user import User
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, OrganizationType
from utils.utils import CommonUtils
from . import dash_district_serializer
from .dash_district_helper import get_user_college_link


class DistrictDetailAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = get_user_college_link(user_id)

        serializer = dash_district_serializer.DistrictDetailsSerializer(
            user_org_link, many=False
        )

        return CustomResponse(response=serializer.data).get_success_response()


class DistrictTopThreeCampusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = get_user_college_link(user_id)

        org_karma_dict = (
            UserOrganizationLink.objects.filter(
                org__org_type=OrganizationType.COLLEGE.value,
                org__district=user_org_link.org.district,
                verified=True,
            )
            .values("org")
            .annotate(total_karma=Sum("user__wallet_user__karma")).order_by('-total_karma', 'org__created_at')
        )

        org_ranks = {
            data["org"]: data["total_karma"] if data["total_karma"] is not None else 0
            for data in org_karma_dict
        }

        sorted_org_ranks = dict(
            sorted(org_ranks.items(), key=lambda x: x[1], reverse=True)
        )

        top_three_orgs = dict(islice(sorted_org_ranks.items(), 3))

        user_org = Organization.objects.filter(id__in=top_three_orgs).distinct()

        serializer = dash_district_serializer.DistrictTopThreeCampusSerializer(
            user_org, many=True, context={"ranks": org_ranks}
        )

        return CustomResponse(response=serializer.data).get_success_response()


class DistrictStudentLevelStatusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = get_user_college_link(user_id)

        district = user_org_link.org.district

        levels = Level.objects.all()
        serializer = dash_district_serializer.DistrictStudentLevelStatusSerializer(
            levels, many=True, context={"district": district}
        )

        return CustomResponse(response=serializer.data).get_success_response()


class DistrictStudentDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = get_user_college_link(user_id)

        rank = (
            Wallet.objects.filter(
                user__user_organization_link_user__org__district=user_org_link.org.district,
                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .distinct()
            .order_by("-karma", '-update_at', "created_at")
            .values(
                "user_id",
                "karma",
            )
        )

        ranks = {user["user_id"]: i + 1 for i, user in enumerate(rank)}

        user_org_links = (
            User.objects.filter(
                user_organization_link_user__org__district=user_org_link.org.district,
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .distinct()
            .annotate(
                user_id=F("id"),
                karma=F("wallet_user__karma"),
                level=F("user_lvl_link_user__level__name"),
            )
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            user_org_links,
            request,
            ["first_name", "last_name", "level"],
            {
                "first_name": "first_name",
                "last_name": "last_name",
                "muid": "muid",
                "karma": "wallet_user__karma",
                "level": "user_lvl_link_user__level__level_order",
            },
        )

        serializer = dash_district_serializer.DistrictStudentDetailsSerializer(
            paginated_queryset.get("queryset"), many=True, context={"ranks": ranks}
        )

        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class DistrictStudentDetailsCSVAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = get_user_college_link(user_id)

        rank = (
            Wallet.objects.filter(
                user__user_organization_link_user__org__district=user_org_link.org.district,
                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .distinct()
            .order_by("-karma", '-updated_at', "created_at")
            .values(
                "user_id",
                "karma",
            )
        )

        ranks = {user["user_id"]: i + 1 for i, user in enumerate(rank)}

        user_org_links = (
            User.objects.filter(
                user_organization_link_user__org__district=user_org_link.org.district,
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .distinct()
            .annotate(
                user_id=F("id"),
                karma=F("wallet_user__karma"),
                level=F("user_lvl_link_user__level__name"),
            )
        )

        serializer = dash_district_serializer.DistrictStudentDetailsSerializer(
            user_org_links, many=True, context={"ranks": ranks}
        )
        return CommonUtils.generate_csv(serializer.data, "District Student Details")


class DistrictsCollageDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = get_user_college_link(user_id)

        organizations = (
            Organization.objects.filter(
                district=user_org_link.org.district,
                org_type=OrganizationType.COLLEGE.value,
            )
            .values("title", "code", "id")
            .annotate(
                level=F("college_org__level"),
            )
        )

        leads = (
            User.objects.filter(
                user_organization_link_user__org__district=user_org_link.org.district,
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                user_role_link_user__role__title=RoleType.CAMPUS_LEAD.value,
            )
            .distinct()
            .annotate(
                college=Case(
                    When(
                        user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                        then=F("user_organization_link_user__org__id"),
                    ),
                    default=None,
                    output_field=CharField(),
                )
            )
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            organizations,
            request,
            [
                "title",
                "code",
            ],
            {
                "title": "title",
                "code": "code",
            },
        )

        serializer = dash_district_serializer.DistrictCollegeDetailsSerializer(
            paginated_queryset.get("queryset"), many=True, context={"leads": leads}
        )

        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class DistrictsCollageDetailsCSVAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = get_user_college_link(user_id)

        organizations = (
            Organization.objects.filter(
                district=user_org_link.org.district,
                org_type=OrganizationType.COLLEGE.value,
            )
            .values("title", "code", "id")
            .annotate(
                level=F("college_org__level"),
            )
        )

        leads = (
            User.objects.filter(
                user_organization_link_user__org__district=user_org_link.org.district,
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                user_role_link_user__role__title=RoleType.CAMPUS_LEAD.value,
            )
            .distinct()
            .annotate(
                college=Case(
                    When(
                        user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                        then=F("user_organization_link_user__org__id"),
                    ),
                    default=None,
                    output_field=CharField(),
                )
            )
        )

        serializer = dash_district_serializer.DistrictCollegeDetailsSerializer(
            organizations, many=True, context={"leads": leads}
        )
        return CommonUtils.generate_csv(serializer.data, "District College Details")
