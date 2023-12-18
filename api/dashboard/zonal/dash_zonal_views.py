from itertools import islice

from django.db.models import Case, CharField, F, Sum, When
from rest_framework.views import APIView

from db.organization import District, Organization, UserOrganizationLink
from db.task import Level, Wallet
from db.user import User
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils
from . import dash_zonal_helper, dash_zonal_serializer


class ZonalDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = dash_zonal_helper.get_user_college_link(user_id)

        serializer = dash_zonal_serializer.ZonalDetailsSerializer(
            user_org_link, many=False
        )
        return CustomResponse(response=serializer.data).get_success_response()


class ZonalTopThreeDistrictAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = dash_zonal_helper.get_user_college_link(user_id)

        district_karma_dict = (
            UserOrganizationLink.objects.filter(
                org__org_type=OrganizationType.COLLEGE.value,
                org__district__zone=user_org_link.org.district.zone,
                verified=True,
            )
            .values("org__district")
            .annotate(total_karma=Sum("user__wallet_user__karma"))
        )

        district_ranks = {
            data["org__district"]: data["total_karma"]
            if data["total_karma"] is not None
            else 0
            for data in district_karma_dict
        }

        district_ranks = dict(
            sorted(district_ranks.items(), key=lambda x: x[1], reverse=True)
        )

        top_districts = dict(islice(district_ranks.items(), 3))

        org_user_district = District.objects.filter(id__in=top_districts).distinct()

        serializer = dash_zonal_serializer.ZonalTopThreeDistrictSerializer(
            org_user_district, many=True, context={"ranks": district_ranks}
        )

        return CustomResponse(response=serializer.data).get_success_response()


class ZonalStudentLevelStatusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = dash_zonal_helper.get_user_college_link(user_id)

        zone = user_org_link.org.district.zone

        levels = Level.objects.all()
        serializer = dash_zonal_serializer.ZonalStudentLevelStatusSerializer(
            levels, many=True, context={"zone": zone}
        )
        return CustomResponse(response=serializer.data).get_success_response()


class ZonalStudentDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = dash_zonal_helper.get_user_college_link(user_id)

        rank = (
            Wallet.objects.filter(
                user__user_organization_link_user__org__district__zone=user_org_link.org.district.zone,
                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .distinct()
            .order_by("-karma", "-updated_at", "created_at")
            .values(
                "user_id",
                "karma",
            )
        )

        ranks = {user["user_id"]: i + 1 for i, user in enumerate(rank)}

        user_org_links = (
            User.objects.filter(
                user_organization_link_user__org__district__zone=user_org_link.org.district.zone,
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
            ["full_name", "level"],
            {
                "full_name": "full_name",
                "muid": "muid",
                "karma": "wallet_user__karma",
                "level": "user_lvl_link_user__level__level_order",
            },
        )

        serializer = dash_zonal_serializer.ZonalStudentDetailsSerializer(
            paginated_queryset.get("queryset"), many=True, context={"ranks": ranks}
        )

        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class ZonalStudentDetailsCSVAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = dash_zonal_helper.get_user_college_link(user_id)

        rank = (
            Wallet.objects.filter(
                user__user_organization_link_user__org__district__zone=user_org_link.org.district.zone,
                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .distinct()
            .order_by("-karma", "-updated_at", "created_at")
            .values(
                "user_id",
                "karma",
            )
        )

        ranks = {user["user_id"]: i + 1 for i, user in enumerate(rank)}

        user_org_links = (
            User.objects.filter(
                user_organization_link_user__org__district__zone=user_org_link.org.district.zone,
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .distinct()
            .annotate(
                user_id=F("id"),
                karma=F("wallet_user__karma"),
                level=F("user_lvl_link_user__level__name"),
            )
        )

        serializer = dash_zonal_serializer.ZonalStudentDetailsSerializer(
            user_org_links, many=True, context={"ranks": ranks}
        )
        return CommonUtils.generate_csv(serializer.data, "Zonal Student Details")


class ZonalCollegeDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = dash_zonal_helper.get_user_college_link(user_id)

        organizations = (
            Organization.objects.filter(
                district__zone=user_org_link.org.district.zone,
                org_type=OrganizationType.COLLEGE.value,
            )
            .values("title", "code", "id")
            .annotate(
                level=F("college_org__level"),
            )
        )

        leads = (
            User.objects.filter(
                user_organization_link_user__org__district__zone=user_org_link.org.district.zone,
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

        serializer = dash_zonal_serializer.ZonalCollegeDetailsSerializer(
            paginated_queryset.get("queryset"), many=True, context={"leads": leads}
        )

        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class ZonalCollegeDetailsCSVAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = dash_zonal_helper.get_user_college_link(user_id)

        organizations = (
            Organization.objects.filter(
                district__zone=user_org_link.org.district.zone,
                org_type=OrganizationType.COLLEGE.value,
            )
            .values("title", "code", "id")
            .annotate(
                level=F("college_org__level"),
            )
        )

        leads = (
            User.objects.filter(
                user_organization_link_user__org__district__zone=user_org_link.org.district.zone,
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

        serializer = dash_zonal_serializer.ZonalCollegeDetailsSerializer(
            organizations, many=True, context={"leads": leads}
        )
        return CommonUtils.generate_csv(serializer.data, "Zonal College Details")
