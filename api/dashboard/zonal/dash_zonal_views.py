from rest_framework.views import APIView
from rest_framework.response import Response

from db.organization import UserOrganizationLink, Zone
from db.user import User
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils
from . import dash_zonal_serializer


class ZonalStudentsAPI(APIView):
    # authentication_classes = [CustomizePermission]

    # @RoleRequired(roles=[RoleType.ZONAL_CAMPUS_LEAD])
    def get(self, request):
        # user_id = JWTUtils.fetch_user_id(request)

        user_id = "3905c96e-a08d-47cc-85a9-b75a469eec70"

        user_org_link = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value, user_id=user_id
        ).first()

        user_zone = user_org_link.org.district.zone
        users_in_zone = UserOrganizationLink.objects.filter(
            org__district__zone=user_zone
        ).values("user")

        user_queryset = User.objects.filter(id__in=users_in_zone)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            user_queryset, request, ["first_name", "last_name", "email", "mobile", "mu_id"]
        )
        serializer = dash_zonal_serializer.ZonalStudents(paginated_queryset.get("queryset"), many=True)

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class ZonalStudentsCSV(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.CAMPUS_AMBASSADOR])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = UserOrganizationLink.objects.filter(
            user_id=user_id, org__org_type=OrganizationType.COLLEGE.value
        ).first()
        user_org_links = UserOrganizationLink.objects.filter(
            org_id=user_org_link.org_id
        )

        serializer = serializers.UserOrgSerializer(user_org_links, many=True)
        return CommonUtils.generate_csv(serializer.data, "Campus Details")


# class CampusDetailsAPI(APIView):
#     authentication_classes = [CustomizePermission]

#     @RoleRequired(roles=[RoleType.CAMPUS_AMBASSADOR])
#     def get(self, request):
#         user_id = JWTUtils.fetch_user_id(request)
#         user_org_link = UserOrganizationLink.objects.filter(
#             user_id=user_id, org__org_type=OrganizationType.COLLEGE.value).first()
#         serializer = serializers.CollegeSerializer(user_org_link, many=False)
#         return CustomResponse(response=serializer.data).get_success_response()
