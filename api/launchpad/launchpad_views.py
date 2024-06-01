from django.db.models import Sum, Max, Prefetch, F, OuterRef, Subquery, IntegerField

from rest_framework.views import APIView

from .serializers import LaunchpadLeaderBoardSerializer
from utils.response import CustomResponse
from utils.utils import CommonUtils
from db.user import User
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
        
        users = (
            User.objects.filter(
                karma_activity_log_user__task__event="launchpad",
                karma_activity_log_user__appraiser_approved=True,
                karma_activity_log_user__task__hashtag="#lp24-introduction",
            ).prefetch_related(
                Prefetch(
                    "user_organization_link_user",
                    queryset=UserOrganizationLink.objects.filter(
                        org__org_type__in=["College", "School", "Company", "Community"]
                    ),
                )
            )
            .annotate(
                karma=Subquery(total_karma_subquery, output_field=IntegerField()),
                org=F("user_organization_link_user__org__title"),
                district_name=F("user_organization_link_user__org__district__name"),
                state=F("user_organization_link_user__org__district__zone__state__name"),
                time_=Max("karma_activity_log_user__created_at"),
            )
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            users,
            request,
            ["karma", "org", "district_name", "state", "time_"],
            sort_fields={
                "-karma": "-karma",
                "time_": "time_",
            },
        )

        serializer = LaunchpadLeaderBoardSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )
