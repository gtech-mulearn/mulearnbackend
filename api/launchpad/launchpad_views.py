from django.db.models import (
    Sum,
    Max,
    Prefetch,
    When,
    Case,
    IntegerField,
    F,
    OuterRef,
    Subquery,
)
from django.db.models.functions import Coalesce

from rest_framework.views import APIView

from .serializers import LaunchpadLeaderBoardSerializer
from utils.response import CustomResponse
from utils.utils import CommonUtils
from db.user import User
from db.organization import Organization, District, State
from db.task import KarmaActivityLog


class Leaderboard(APIView):
    def get(self, request):
        karma_subquery = (
            KarmaActivityLog.objects.filter(
                user=OuterRef("id"),
                task__event="launchpad",
                appraiser_approved=True,
                task__hashtag="#lp24-introduction",
            )
            .annotate(total_karma=Sum("karma"))
            .values("total_karma")
        )
        users = (
            User.objects.filter(
                karma_activity_log_user__task__event="launchpad",
                karma_activity_log_user__appraiser_approved=True,
                karma_activity_log_user__task__hashtag="#lp24-introduction",
            )
            .prefetch_related(
                Prefetch(
                    "user_organization_link_user__org",
                    queryset=Organization.objects.filter(
                        org_type__in=["College", "School", "Company"]
                    )
                    .select_related("district", "district_zone_state_name")
                    .all(),
                )
            )
            .annotate(
                karma=Subquery(karma_subquery, output_field=IntegerField()),
                time_=Max("karma_activity_log_user__created_at"),
                org=F("user_organization_link_user__org__title"),
                district_name=F("district__name"),
                state=F("district__zone__state__name"),
            )
            .values("full_name", "karma", "org", "district_name", "state", "time_")
            .order_by("-karma", "time_")
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            users,
            request,
            ["karma", "org", "district_name", "state", "time_"],
            sort_fields={
                "karma": "karma",
                "org": "org",
                "district_name": "district_name",
                "state": "state",
                "time_": "time_",
            },
        )

        serializer = LaunchpadLeaderBoardSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )
