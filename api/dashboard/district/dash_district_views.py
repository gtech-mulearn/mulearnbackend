from rest_framework.views import APIView

from db.organization import UserOrganizationLink, Organization
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, OrganizationType
from utils.utils import CommonUtils
from . import dash_district_serializer


class DistrictDetailAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = UserOrganizationLink.objects.filter(
            user=user_id,
            org__org_type=OrganizationType.COLLEGE.value).first()

        serializer = dash_district_serializer.DistrictDetailsSerializer(user_org_link, many=False)
        return CustomResponse(response=serializer.data).get_success_response()


class DistrictTopThreeCampusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = UserOrganizationLink.objects.filter(
            user=user_id,
            org__org_type=OrganizationType.COLLEGE.value).first()

        if user_org_link.org.district is None:
            return CustomResponse(
                general_message=['Zonal Lead has no district']).get_failure_response()

        user_organizations = Organization.objects.filter(
            district=user_org_link.org.district,
            user_organization_link_org_id__user__total_karma_user__isnull=False).distinct()

        serializer = dash_district_serializer.DistrictTopThreeCampusSerializer(user_organizations, many=True).data
        sorted_serializer = sorted(serializer, key=lambda x: x['rank'])[:3]

        return CustomResponse(response=sorted_serializer).get_success_response()


class DistrictStudentLevelStatusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = UserOrganizationLink.objects.filter(
            user=user_id,
            org__org_type=OrganizationType.COLLEGE.value).first()

        if user_org_link.org.district is None:
            return CustomResponse(
                general_message=['Zonal Lead has no district']).get_failure_response()

        organizations = Organization.objects.filter(
            district=user_org_link.org.district,
            org_type=OrganizationType.COLLEGE.value)

        serializer = dash_district_serializer.DistrictStudentLevelStatusSerializer(organizations, many=True)
        return CustomResponse(response=serializer.data).get_success_response()


class DistrictStudentDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = UserOrganizationLink.objects.filter(
            user_id=user_id,
            org__org_type=OrganizationType.COLLEGE.value).first()

        if user_org_link.org.district is None:
            return CustomResponse(
                general_message=['Zonal Lead has no district']).get_failure_response()

        user_org_links = UserOrganizationLink.objects.filter(
            org__district=user_org_link.org.district,
            org__org_type=OrganizationType.COLLEGE.value)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            user_org_links, request,
            ['user__first_name'],
            {'name': 'user__full_name',
             'muid': 'user__mu_id',
             'karma': 'user__total_karma_user__karma',
             'level': 'user__user_level_link_user__level__level_order'})

        serializer = dash_district_serializer.DistrictStudentDetailsSerializer(
            paginated_queryset.get('queryset'), many=True).data

        return CustomResponse(
            response={"data": serializer, 'pagination': paginated_queryset.get(
                'pagination')}).get_success_response()


class DistrictStudentDetailsCSVAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = UserOrganizationLink.objects.filter(
            user_id=user_id,
            org__org_type=OrganizationType.COLLEGE.value).first()

        if user_org_link.org.district is None:
            return CustomResponse(
                general_message=['Zonal Lead has no district']).get_failure_response()

        user_org_links = UserOrganizationLink.objects.filter(
            org__district=user_org_link.org.district,
            org__org_type=OrganizationType.COLLEGE.value)

        serializer = dash_district_serializer.DistrictStudentDetailsSerializer(user_org_links, many=True)
        return CommonUtils.generate_csv(serializer.data, 'District Details')


class ListAllDistrictsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org = Organization.objects.filter(
            user_organization_link_org_id__user_id=user_id,
            org_type=OrganizationType.COLLEGE.value).first()

        if user_org.district is None:
            return CustomResponse(
                general_message=['Zonal Lead has no district']).get_failure_response()

        organizations = Organization.objects.filter(
            district=user_org.district,
            org_type=OrganizationType.COLLEGE.value)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            organizations, request,
            ['title', 'code', 'user_organization_link_org_id__user__first_name',
             'user_organization_link_org_id__user__mobile'],
            {'title': 'title',
             'code': 'code',
             'lead': 'user_organization_link_org_id__user__first_name',
             'mobile': 'user_organization_link_org_id__user__mobile',
             })

        serializer = dash_district_serializer.ListAllDistrictsSerializer(
            paginated_queryset.get('queryset'), many=True).data

        return CustomResponse(
            response={"data": serializer, 'pagination': paginated_queryset.get(
                'pagination')}).get_success_response()


class ListAllDistrictsCSVAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org = Organization.objects.filter(
            user_organization_link_org_id__user_id=user_id,
            org_type=OrganizationType.COLLEGE.value).first()

        if user_org.district is None:
            return CustomResponse(
                general_message=['Zonal Lead has no district']).get_failure_response()

        organizations = Organization.objects.filter(
            district=user_org.district,
            org_type=OrganizationType.COLLEGE.value)

        serializer = dash_district_serializer.ListAllDistrictsSerializer(organizations, many=True)
        return CommonUtils.generate_csv(serializer.data, 'District Details')
