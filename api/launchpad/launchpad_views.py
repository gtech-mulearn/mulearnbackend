from django.db.models import Sum, Max, Prefetch, When, Case, IntegerField, F

from rest_framework.views import APIView

from .serializers import LaunchpadLeaderBoardSerializer
from utils.response import CustomResponse
from utils.utils import CommonUtils
from db.user import User
from db.organization import UserOrganizationLink


class Leaderboard(APIView):
    def get(self, request):
        users = (
            User.objects.filter(
                karma_activity_log_user__task__event="launchpad",
                karma_activity_log_user__appraiser_approved=True,
                karma_activity_log_user__task__hashtag="#lp24-introduction",
            )
            .prefetch_related(
                Prefetch(
                    "user_organization_link_user__title",
                    queryset=UserOrganizationLink.objects.all(),
                    to_attr="org",
                ),
            ).select_related("district", "district__zone__state")
            .annotate(
                karma=Sum(
                    Case(
                        When(
                            karma_activity_log_user__task__event="launchpad",
                            karma_activity_log_user__appraiser_approved=True,
                            then="karma_activity_log_user__karma",
                        ),
                        default=0,
                        output_field=IntegerField()
                    )
                ),
                time_=Max("karma_activity_log_user__created_at"),
                district_name=F("district__name"),
                state=F("district__zone__state__name"),
            )
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
