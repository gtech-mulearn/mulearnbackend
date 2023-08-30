from itertools import islice

from django.db.models import Sum
from rest_framework.views import APIView

from db.organization import UserOrganizationLink, Organization
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, OrganizationType
from utils.utils import CommonUtils
from . import dash_district_serializer
from .dash_district_helper import get_user_college_link, get_user_college


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

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = get_user_college_link(user_id)

        org_karma_dict = (
            UserOrganizationLink.objects.filter(
                org__district=user_org_link.org.district,
                verified=True,
            )
            .values("org")
            .annotate(total_karma=Sum("user__total_karma_user__karma"))
        )

        org_ranks = {
            data["org"]: data["total_karma"]
            if data["total_karma"] is not None
            else 0
            for data in org_karma_dict
        }

        sorted_org_ranks = dict(
            sorted(org_ranks.items(), key=lambda x: x[1], reverse=True)
        )

        top_three_orgs = dict(islice(sorted_org_ranks.items(), 3))

        user_org = Organization.objects.filter(id__in=top_three_orgs).distinct()

        serializer = dash_district_serializer.DistrictTopThreeCampusSerializer(
            user_org,
            many=True,
            context={"ranks": org_ranks}
        )

        return CustomResponse(response=serializer.data).get_success_response()


class DistrictStudentLevelStatusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = get_user_college_link(user_id)

        if user_org_link.org.district is None:
            return CustomResponse(
                general_message='Zonal Lead has no district'
            ).get_failure_response()

        organizations = Organization.objects.filter(
            district=user_org_link.org.district,
            org_type=OrganizationType.COLLEGE.value
        )

        serializer = dash_district_serializer.DistrictStudentLevelStatusSerializer(
            organizations, many=True
        )

        return CustomResponse(response=serializer.data).get_success_response()


class DistrictStudentDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = get_user_college_link(user_id)

        if user_org_link.org.district is None:
            return CustomResponse(
                general_message='Zonal Lead has no district'
            ).get_failure_response()

        user_org_links = UserOrganizationLink.objects.filter(
            org__district=user_org_link.org.district,
            org__org_type=OrganizationType.COLLEGE.value
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            user_org_links, request,
            ['user__first_name'],
            {'name': 'user__first_name',
             'muid': 'user__mu_id',
             'karma': 'user__total_karma_user__karma',
             'level': 'user__user_lvl_link_user__level__level_order'})

        serializer = dash_district_serializer.DistrictStudentDetailsSerializer(
            paginated_queryset.get(
                'queryset'), many=True).data

        return CustomResponse(
            response={"data": serializer,
                      'pagination': paginated_queryset.get(
                          'pagination')}).get_success_response()


class DistrictStudentDetailsCSVAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = get_user_college_link(user_id)

        if user_org_link.org.district is None:
            return CustomResponse(
                general_message='Zonal Lead has no district'
            ).get_failure_response()

        user_org_links = UserOrganizationLink.objects.filter(
            org__district=user_org_link.org.district,
            org__org_type=OrganizationType.COLLEGE.value
        )

        serializer = dash_district_serializer.DistrictStudentDetailsSerializer(
            user_org_links, many=True
        )

        return CommonUtils.generate_csv(serializer.data, 'District Details')


class DistrictsCollageDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org = get_user_college(user_id)

        if user_org.district is None:
            return CustomResponse(
                general_message='Zonal Lead has no district'
            ).get_failure_response()

        organizations = Organization.objects.filter(
            district=user_org.district,
            org_type=OrganizationType.COLLEGE.value
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            organizations, request,
            ['title',
             'code',
             'user_organization_link_org_id__user__first_name',
             'user_organization_link_org_id__user__mobile'],
            {'title': 'title',
             'code': 'code',
             'lead': 'user_organization_link_org_id__user__first_name',
             'mobile': 'user_organization_link_org_id__user__mobile',
             })

        serializer = dash_district_serializer.DistrictCollegeDetailsSerializer(
            paginated_queryset.get('queryset'), many=True).data

        return CustomResponse(
            response={
                "data": serializer,
                'pagination': paginated_queryset.get(
                    'pagination')}).get_success_response()


class DistrictsCollageDetailsCSVAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.DISTRICT_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org = get_user_college(user_id)

        if user_org.district is None:
            return CustomResponse(
                general_message='Zonal Lead has no district'
            ).get_failure_response()

        organizations = Organization.objects.filter(
            district=user_org.district,
            org_type=OrganizationType.COLLEGE.value
        )

        serializer = dash_district_serializer.DistrictCollegeDetailsSerializer(organizations, many=True)
        return CommonUtils.generate_csv(serializer.data, 'District Details')
