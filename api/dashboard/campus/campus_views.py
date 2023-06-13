from django.db.models import F, IntegerField, Case, When, Value
from rest_framework.views import APIView

from db.organization import UserOrganizationLink
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils
from . import serializers


# class StudentDetailsAPI(APIView):
#     authentication_classes = [CustomizePermission]
#
#     @RoleRequired(roles=[RoleType.CAMPUS_LEAD])
#     def get(self, request):
#         user_id = JWTUtils.fetch_user_id(request)
#         user_org_link = UserOrganizationLink.objects.filter(user_id=user_id,
#                                                             org__org_type=OrganizationType.COLLEGE.value).first()
#         user_org_links = UserOrganizationLink.objects.filter(org_id=user_org_link.org_id)
#         paginated_queryset = CommonUtils.get_paginated_queryset(user_org_links, request, ['user__first_name'])
#         serializer = serializers.UserOrgSerializer(paginated_queryset.get('queryset'), many=True).data
#         sorted_persons = sorted(serializer, key=lambda x: x['karma'], reverse=True)
#         for i, person in enumerate(sorted_persons):
#             person['rank'] = i + 1
#
#         return CustomResponse(response={"data": sorted_persons,
#                                         'pagination': paginated_queryset.get('pagination')}).get_success_response()

class StudentDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.CAMPUS_LEAD])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_links = UserOrganizationLink.objects.filter(
            user_id=user_id,
            org__org_type=OrganizationType.COLLEGE.value
        ).values('org_id')

        queryset = UserOrganizationLink.objects.filter(
            org_id__in=user_org_links,
            user__total_karma_user__isnull=False
        ).annotate(
            fullname=F('user__fullname'),
            muid=F('user__mu_id'),
            karma=F('user__total_karma_user__karma'),
            rank=Case(
                When(user__total_karma_user__karma=F('karma'), then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            level=F('user__userlvllink__level__name')
        ).order_by('-karma')

        # paginated_queryset = CommonUtils.get_paginated_queryset(queryset, request, ['fullname'])
        serializer = serializers.UserOrgSerializer(queryset, many=True)

        return CustomResponse(response={"data": serializer.data}).get_success_response()

        # return CustomResponse(response={"data": serializer,
        #                                 'pagination': paginated_queryset.get('pagination')}).get_success_response()


class StudentDetailsCSVAPI(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.CAMPUS_LEAD])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = UserOrganizationLink.objects.filter(user_id=user_id,
                                                            org__org_type=OrganizationType.COLLEGE.value).first()
        user_org_links = UserOrganizationLink.objects.filter(
            org_id=user_org_link.org_id)

        serializer = serializers.UserOrgSerializer(user_org_links, many=True)
        return CommonUtils.generate_csv(serializer.data, 'Campus Details')


class CampusDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.CAMPUS_LEAD])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = UserOrganizationLink.objects.filter(
            user_id=user_id, org__org_type=OrganizationType.COLLEGE.value).first()
        serializer = serializers.CollegeSerializer(user_org_link, many=False)
        return CustomResponse(response=serializer.data).get_success_response()
