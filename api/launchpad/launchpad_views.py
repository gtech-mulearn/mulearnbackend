from django.db.models import Sum, Max, Prefetch, F, OuterRef, Subquery, IntegerField

from rest_framework.views import APIView

from .serializers import LaunchpadLeaderBoardSerializer, LaunchpadParticipantsSerializer
from utils.response import CustomResponse
from utils.utils import CommonUtils
from db.user import User, UserRoleLink
from db.organization import UserOrganizationLink
from db.task import KarmaActivityLog



class Leaderboard(APIView):
    def get(self, request):
        total_karma_subquery = KarmaActivityLog.objects.filter(
            user=OuterRef('id'),
            task__event='launchpad',
            appraiser_approved=True,
        ).values('user').annotate(
            total_karma=Sum('karma')
        ).values('total_karma')
        allowed_org_types = ["College", "School", "Company"]

        intro_task_completed_users = KarmaActivityLog.objects.filter(
            task__event='launchpad',
            appraiser_approved=True,
            task__hashtag='#lp24-introduction',
        ).values('user')
        
        users = User.objects.filter(
            karma_activity_log_user__task__event="launchpad",
            karma_activity_log_user__appraiser_approved=True,
            id__in=intro_task_completed_users
        ).prefetch_related(
            Prefetch(
                "user_organization_link_user",
                queryset=UserOrganizationLink.objects.filter(org__org_type__in=allowed_org_types),
            )
        ).filter(
            user_organization_link_user__id__in=UserOrganizationLink.objects.filter(
                org__org_type__in=allowed_org_types
            ).values("id")
        ).annotate(
            karma=Subquery(total_karma_subquery, output_field=IntegerField()),
            org=F("user_organization_link_user__org__title"),
            district_name=F("user_organization_link_user__org__district__name"),
            state=F("user_organization_link_user__org__district__zone__state__name"),
            time_=Max("karma_activity_log_user__created_at"),
        ).order_by("-karma", "time_")

        paginated_queryset = CommonUtils.get_paginated_queryset(
            users,
            request,
            ["full_name", "karma", "org", "district_name", "state"]
        )

        serializer = LaunchpadLeaderBoardSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class ListParticipantsAPI(APIView):
    def get(self, request):
        allowed_org_types = ["College", "School", "Company"]
        allowed_levels = [
            "IEEE Launchpad Level 1",
            "IEEE Launchpad Level 2",
            "IEEE Launchpad Level 3",
            "IEEE Launchpad Level 4"
        ]

        intro_task_completed_users = KarmaActivityLog.objects.filter(
            task__event='launchpad',
            appraiser_approved=True,
            task__hashtag='#lp24-introduction',
        ).values('user')

        users = User.objects.filter(
            karma_activity_log_user__task__event="launchpad",
            karma_activity_log_user__appraiser_approved=True,
            id__in=intro_task_completed_users
        ).prefetch_related(
            Prefetch(
                "user_organization_link_user",
                queryset=UserOrganizationLink.objects.filter(org__org_type__in=allowed_org_types),
            ),
            Prefetch(
                "user_role_link_user",
                queryset=UserRoleLink.objects.filter(verified=True, role__title__in=allowed_levels).select_related('role')
            )
        ).filter(
            user_organization_link_user__id__in=UserOrganizationLink.objects.filter(
                org__org_type__in=allowed_org_types
            ).values("id")
        ).annotate(
            org=F("user_organization_link_user__org__title"),
            district_name=F("user_organization_link_user__org__district__name"),
            state=F("user_organization_link_user__org__district__zone__state__name"),
            level=F("user_role_link_user__role__title"),
            time_=Max("karma_activity_log_user__created_at"),
        ).filter(
            level__in=allowed_levels
        ).distinct()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            users,
            request,
            ["full_name", "level", "org", "district_name", "state"]
        )

        serializer = LaunchpadParticipantsSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class LaunchpadDetailsCount(APIView):
    def get(self, request):
        allowed_org_types = ["College", "School", "Company"]
        allowed_levels = [
            "IEEE Launchpad Level 1",
            "IEEE Launchpad Level 2",
            "IEEE Launchpad Level 3",
            "IEEE Launchpad Level 4"
        ]

        intro_task_completed_users = KarmaActivityLog.objects.filter(
            task__event='launchpad',
            appraiser_approved=True,
            task__hashtag='#lp24-introduction',
        ).values('user')

        users = User.objects.filter(
            karma_activity_log_user__task__event="launchpad",
            karma_activity_log_user__appraiser_approved=True,
            id__in=intro_task_completed_users
        ).prefetch_related(
            Prefetch(
                "user_organization_link_user",
                queryset=UserOrganizationLink.objects.filter(org__org_type__in=allowed_org_types),
            ),
            Prefetch(
                "user_role_link_user",
                queryset=UserRoleLink.objects.filter(verified=True,
                                                     role__title__in=allowed_levels).select_related('role')
            )
        ).filter(
            user_organization_link_user__id__in=UserOrganizationLink.objects.filter(
                org__org_type__in=allowed_org_types
            ).values("id")
        ).annotate(
            org=F("user_organization_link_user__org__title"),
            district_name=F("user_organization_link_user__org__district__name"),
            state=F("user_organization_link_user__org__district__zone__state__name"),
            level=F("user_role_link_user__role__title"),
            time_=Max("karma_activity_log_user__created_at"),
        ).filter(
            level__in=allowed_levels
        ).distinct()

        # Count participants at each level
        level_counts = {
            "total_participants": users.count(),
            "Level_1": users.filter(level="IEEE Launchpad Level 1").count(),
            "Level_2": users.filter(level="IEEE Launchpad Level 2").count(),
            "Level_3": users.filter(level="IEEE Launchpad Level 3").count(),
            "Level_4": users.filter(level="IEEE Launchpad Level 4").count(),
        }

        return CustomResponse(response=level_counts).get_success_response()
