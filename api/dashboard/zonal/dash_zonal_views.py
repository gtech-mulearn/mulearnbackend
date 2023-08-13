from rest_framework.views import APIView

from db.organization import UserOrganizationLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from . import dash_zonal_serializer


# class ZonalStudentsAPI(APIView):
#     authentication_classes = [CustomizePermission]
#
#     @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
#     def get(self, request):
#         user_id = JWTUtils.fetch_user_id(request)
#
#         user_org_link = UserOrganizationLink.objects.filter(
#             org__org_type=OrganizationType.COLLEGE.value, user_id=user_id, verified=True
#         ).first()
#
#         user_zone = user_org_link.org.district.zone
#         users_in_zone = UserOrganizationLink.objects.filter(
#             org__district__zone=user_zone
#         ).values("user")
#
#         user_queryset = User.objects.filter(id__in=users_in_zone).distinct()
#
#         paginated_queryset = CommonUtils.get_paginated_queryset(
#             user_queryset,
#             request,
#             ["first_name", "last_name", "email", "mobile", "mu_id"],
#         )
#
#         serializer = dash_zonal_serializer.ZonalStudents(
#             paginated_queryset["queryset"],
#             many=True,
#             context={"queryset": user_queryset},
#         )
#
#         return CustomResponse().paginated_response(
#             data=serializer.data, pagination=paginated_queryset.get("pagination")
#         )
#
#
# class ZonalStudentsCSV(APIView):
#     authentication_classes = [CustomizePermission]
#
#     @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
#     def get(self, request):
#         user_id = JWTUtils.fetch_user_id(request)
#
#         user_org_link = UserOrganizationLink.objects.filter(
#             org__org_type=OrganizationType.COLLEGE.value, user_id=user_id, verified=True
#         ).first()
#
#         user_zone = user_org_link.org.district.zone
#         users_in_zone = UserOrganizationLink.objects.filter(
#             org__district__zone=user_zone
#         ).values("user")
#
#         user_queryset = User.objects.filter(id__in=users_in_zone).distinct()
#
#         serializer = dash_zonal_serializer.ZonalStudents(
#             user_queryset,
#             many=True,
#             context={"queryset": user_queryset},
#         )
#
#         return CommonUtils.generate_csv(serializer.data, "Zonal Student Details")
#
#
# class ZonalCampusAPI(APIView):
#     authentication_classes = [CustomizePermission]
#
#     @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
#     def get(self, request):
#         user_id = JWTUtils.fetch_user_id(request)
#
#         user_org_link = UserOrganizationLink.objects.filter(
#             org__org_type=OrganizationType.COLLEGE.value, user_id=user_id, verified=True
#         ).first()
#
#         campus_zone = user_org_link.org.district.zone
#
#         organizations_in_zone = (
#             Organization.objects.select_related("district", "district__zone")
#             .filter(district__zone=campus_zone, org_type=OrganizationType.COLLEGE.value)
#             .distinct()
#             .prefetch_related("user_organization_link_org_id", "user_organization_link_org_id__user__total_karma_user")
#             .annotate(total_members=Count("user_organization_link_org_id"))
#             .annotate(active_members=Count("user_organization_link_org_id",
#                                            filter=Q(user_organization_link_org_id__verified=True,
#                                                     user_organization_link_org_id__user__active=True)))
#             .annotate(total_karma=Coalesce(Sum("user_organization_link_org_id__user__total_karma_user__karma"), 0))
#         )
#
#         paginated_queryset = CommonUtils.get_paginated_queryset(
#             organizations_in_zone,
#             request,
#             ["title", "code", "org_type"],
#         )
#
#         serializer = dash_zonal_serializer.ZonalCampus(
#             paginated_queryset["queryset"],
#             many=True,
#             context={"queryset": organizations_in_zone},
#         )
#
#         return CustomResponse().paginated_response(
#             data=serializer.data, pagination=paginated_queryset.get("pagination")
#         )
#
#
# class ZonalCampusCSV(APIView):
#     authentication_classes = [CustomizePermission]
#
#     @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
#     def get(self, request):
#         user_id = JWTUtils.fetch_user_id(request)
#
#         user_org_link = UserOrganizationLink.objects.filter(
#             org__org_type=OrganizationType.COLLEGE.value, user_id=user_id, verified=True
#         ).first()
#
#         campus_zone = user_org_link.org.district.zone
#
#         organizations_in_zone = (
#             Organization.objects.select_related("district", "district__zone")
#             .filter(district__zone=campus_zone, org_type=OrganizationType.COLLEGE.value)
#             .distinct()
#             .prefetch_related("user_organization_link_org_id", "user_organization_link_org_id__user__total_karma_user")
#             .annotate(total_members=Count("user_organization_link_org_id"))
#             .annotate(active_members=Count("user_organization_link_org_id",
#                                            filter=Q(user_organization_link_org_id__verified=True,
#                                                     user_organization_link_org_id__user__active=True)))
#             .annotate(total_karma=Coalesce(Sum("user_organization_link_org_id__user__total_karma_user__karma"), 0))
#         )
#
#         serializer = dash_zonal_serializer.ZonalCampus(
#             organizations_in_zone,
#             many=True,
#             context={"queryset": organizations_in_zone},
#         )
#
#         return CommonUtils.generate_csv(serializer.data, "Zonal Campus Details")


class ZonalDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = UserOrganizationLink.objects.filter(user=user_id).first()
        serializer = dash_zonal_serializer.ZonalDetailsSerializer(user_org_link, many=False)
        return CustomResponse(response=serializer.data).get_success_response()


class ZonalTopThreeDistrictAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = UserOrganizationLink.objects.filter(user=user_id).first()
        org_user_district = UserOrganizationLink.objects.filter(org__district__zone__name=user_org_link.org.district.
                                                                zone.name)
        serializer = dash_zonal_serializer.ZonalTopThreeDistrictSerializer(org_user_district, many=True).data
        sorted_serializer = sorted(serializer, key=lambda x: x['rank'])[:3]
        return CustomResponse(response=sorted_serializer).get_success_response()


class ZonalStudentLevelStatusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        district_id = request.data.get('district_id')
        org_user_district = UserOrganizationLink.objects.filter(org__district__id=district_id)
        serializer = dash_zonal_serializer.ZonalStudentLevelStatusSerializer(org_user_district, many=True)
        return CustomResponse(response=serializer.data).get_success_response()


class ZonalStudentDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
    def get(self, request, url):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = UserOrganizationLink.objects.filter(user_id=user_id).first()
        user_org_links = UserOrganizationLink.objects.filter(org__district__zone_id=user_org_link.org.district.zone.id,
                                                             org__org_type=url)

        paginated_queryset = CommonUtils.get_paginated_queryset(user_org_links, request, ['user__first_name'],
                                                                {'name': 'user__full_name',
                                                                 'muid': 'user__mu_id',
                                                                 'karma': 'user__total_karma_user__karma',
                                                                 'level': 'user__user_level_link_user__level__'
                                                                          'level_order'})
        serializer = dash_zonal_serializer.ZonalStudentDetailsSerializer(paginated_queryset.get('queryset'),
                                                                         many=True).data
        return CustomResponse(response={"data": serializer, 'pagination': paginated_queryset.get(
            'pagination')}).get_success_response()


class ZonalStudentDetailsCSVAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
    def get(self, request, url):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = UserOrganizationLink.objects.filter(user_id=user_id).first()
        user_org_links = UserOrganizationLink.objects.filter(org__district__zone_id=user_org_link.org.district.zone.id,
                                                             org__org_type=url)
        serializer = dash_zonal_serializer.ZonalStudentDetailsSerializer(user_org_links, many=True)
        return CommonUtils.generate_csv(serializer.data, 'Zonal Details')
