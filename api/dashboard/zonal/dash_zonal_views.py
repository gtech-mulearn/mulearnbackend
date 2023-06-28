from django.db.models import Count, Q
from django.db.models import Sum
from django.db.models.functions import Coalesce
from rest_framework.views import APIView

from db.organization import Organization, UserOrganizationLink
from db.user import User
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils
from . import dash_zonal_serializer


class ZonalStudentsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value, user_id=user_id, verified=True
        ).first()

        user_zone = user_org_link.org.district.zone
        users_in_zone = UserOrganizationLink.objects.filter(
            org__district__zone=user_zone
        ).values("user")

        user_queryset = User.objects.filter(id__in=users_in_zone).distinct()

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

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value, user_id=user_id, verified=True
        ).first()

        user_zone = user_org_link.org.district.zone
        users_in_zone = UserOrganizationLink.objects.filter(
            org__district__zone=user_zone
        ).values("user")

        user_queryset = User.objects.filter(id__in=users_in_zone).distinct()

        serializer = dash_zonal_serializer.ZonalStudents(
            user_queryset,
            many=True,
            context={"queryset": user_queryset},
        )

        return CommonUtils.generate_csv(serializer.data, "Zonal Student Details")


class ZonalCampusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value, user_id=user_id, verified=True
        ).first()

        campus_zone = user_org_link.org.district.zone

        organizations_in_zone = (
            Organization.objects.select_related("district", "district__zone")
            .filter(district__zone=campus_zone, org_type=OrganizationType.COLLEGE.value)
            .distinct()
            .prefetch_related("user_organization_link_org_id", "user_organization_link_org_id__user__total_karma_user")
            .annotate(total_members=Count("user_organization_link_org_id"))
            .annotate(active_members=Count("user_organization_link_org_id",
                                           filter=Q(user_organization_link_org_id__verified=True,
                                                    user_organization_link_org_id__user__active=True)))
            .annotate(total_karma=Coalesce(Sum("user_organization_link_org_id__user__total_karma_user__karma"), 0))
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            organizations_in_zone,
            request,
            ["title", "code", "org_type"],
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

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value, ])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value, user_id=user_id, verified=True
        ).first()

        campus_zone = user_org_link.org.district.zone

        organizations_in_zone = (
            Organization.objects.select_related("district", "district__zone")
            .filter(district__zone=campus_zone, org_type=OrganizationType.COLLEGE.value)
            .distinct()
            .prefetch_related("user_organization_link_org_id", "user_organization_link_org_id__user__total_karma_user")
            .annotate(total_members=Count("user_organization_link_org_id"))
            .annotate(active_members=Count("user_organization_link_org_id",
                                           filter=Q(user_organization_link_org_id__verified=True,
                                                    user_organization_link_org_id__user__active=True)))
            .annotate(total_karma=Coalesce(Sum("user_organization_link_org_id__user__total_karma_user__karma"), 0))
        )

        serializer = dash_zonal_serializer.ZonalCampus(
            organizations_in_zone,
            many=True,
            context={"queryset": organizations_in_zone},
        )

        return CommonUtils.generate_csv(serializer.data, "Zonal Campus Details")
