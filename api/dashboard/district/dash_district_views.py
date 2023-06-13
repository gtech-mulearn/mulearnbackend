from rest_framework.views import APIView

from db.organization import Organization, UserOrganizationLink
from db.user import User
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils
from . import dash_district_serializer


class DistrictStudentsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value, user_id=user_id, verified=True
        ).first()

        user_district = user_org_link.org.district

        users_in_district = UserOrganizationLink.objects.filter(
            org__district=user_district
        ).values("user")

        user_queryset = User.objects.filter(id__in=users_in_district).distinct()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            user_queryset,
            request,
            ["first_name", "last_name", "email", "mobile", "mu_id"],
        )

        serializer = dash_district_serializer.DistrictStudents(
            paginated_queryset["queryset"],
            many=True,
            context={"queryset": user_queryset},
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class DistrictStudentsCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value, user_id=user_id, verified=True
        ).first()

        user_district = user_org_link.org.district

        users_in_district = UserOrganizationLink.objects.filter(
            org__district=user_district
        ).values("user")

        user_queryset = User.objects.filter(id__in=users_in_district).distinct()

        serializer = dash_district_serializer.DistrictStudents(
            user_queryset,
            many=True,
            context={"queryset": user_queryset},
        )

        return CommonUtils.generate_csv(serializer.data, "District Student Details")


class DistrictCampusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value, user_id=user_id, verified=True
        ).first()

        campus_district = user_org_link.org.district

        organizations_in_district = Organization.objects.filter(
            district=campus_district,
            org_type=OrganizationType.COLLEGE.value,
        ).distinct()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            organizations_in_district,
            request,
            ["title", "code", "org_type"],
        )

        serializer = dash_district_serializer.DistrictCampus(
            paginated_queryset["queryset"],
            many=True,
            context={"queryset": organizations_in_district},
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class DistrictCampusCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value, user_id=user_id, verified=True
        ).first()

        campus_district = user_org_link.org.district

        organizations_in_district = Organization.objects.filter(
            district=campus_district,
            org_type=OrganizationType.COLLEGE.value,
        ).distinct()

        serializer = dash_district_serializer.DistrictCampus(
            organizations_in_district,
            many=True,
            context={"queryset": organizations_in_district},
        )

        return CommonUtils.generate_csv(serializer.data, "District Campus Details")
