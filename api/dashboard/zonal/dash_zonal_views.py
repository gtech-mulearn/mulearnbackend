from rest_framework.views import APIView

from db.organization import Organization, UserOrganizationLink
from db.user import User
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils
from . import dash_zonal_serializer


class ZonalStudentsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.ZONAL_CAMPUS_LEAD])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        # user_id = "3905c96e-a08d-47cc-85a9-b75a469eec70"

        user_org_link = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value, user_id=user_id
        ).first()

        user_zone = user_org_link.org.district.zone
        users_in_zone = UserOrganizationLink.objects.filter(
            org__district__zone=user_zone
        ).values("user")

        user_queryset = User.objects.filter(id__in=users_in_zone)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            user_queryset,
            request,
            ["first_name", "last_name", "email", "mobile", "mu_id"],
        )

        serializer = dash_zonal_serializer.ZonalStudents(
            paginated_queryset["queryset"],
            many=True,
            context={"queryset": user_queryset},
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class ZonalStudentsCSV(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.CAMPUS_LEAD])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        # user_id = "3905c96e-a08d-47cc-85a9-b75a469eec70"

        user_org_link = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value, user_id=user_id
        ).first()

        user_zone = user_org_link.org.district.zone
        users_in_zone = UserOrganizationLink.objects.filter(
            org__district__zone=user_zone
        ).values("user")

        user_queryset = User.objects.filter(id__in=users_in_zone)

        serializer = dash_zonal_serializer.ZonalStudents(
            user_queryset,
            many=True,
            context={"queryset": user_queryset},
        )

        return CommonUtils.generate_csv(serializer.data, "Zonal Student Details")


class ZonalCampusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.ZONAL_CAMPUS_LEAD])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        # user_id = "00d1ba08-bb83-4374-9864-d3ce9de6bd81"

        user_org_link = UserOrganizationLink.objects.select_related(
            "org", "org__district", "org__district__zone"
        ).get(org__org_type=OrganizationType.COLLEGE.value, user_id=user_id)

        campus_zone = user_org_link.org.district.zone

        organizations_in_zone = Organization.objects.select_related(
            "district", "district__zone"
        ).filter(district__zone=campus_zone, org_type=OrganizationType.COLLEGE.value)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            organizations_in_zone,
            request,
            [
                "title",
                "code",
                "org_type",
                "district_name",
            ],
        )

        serializer = dash_zonal_serializer.ZonalCampus(
            paginated_queryset["queryset"],
            many=True,
            context={"queryset": organizations_in_zone},
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class ZonalCampusCSV(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.ZONAL_CAMPUS_LEAD])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        # user_id = "00d1ba08-bb83-4374-9864-d3ce9de6bd81"

        user_org_link = UserOrganizationLink.objects.select_related(
            "org", "org__district", "org__district__zone"
        ).get(
            org__org_type=OrganizationType.COLLEGE.value, user_id=user_id, verified=True
        )

        campus_zone = user_org_link.org.district.zone

        organizations_in_zone = Organization.objects.select_related(
            "district", "district__zone"
        ).filter(district__zone=campus_zone, org_type=OrganizationType.COLLEGE.value)

        verified_organizations = list(
            organizations_in_zone.filter(user_organization_link_org_id__verified=True)
        )

        serializer = dash_zonal_serializer.ZonalCampus(
            verified_organizations,
            many=True,
            context={"queryset": verified_organizations},
        )

        return CommonUtils.generate_csv(serializer.data, "Zonal Campus Details")
