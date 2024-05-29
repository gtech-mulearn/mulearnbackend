from django.db.models import Sum, Max, F

from rest_framework.views import APIView

from .serializers import LaunchpadLeaderBoardSerializer
from utils.response import CustomResponse
from utils.utils import CommonUtils
from db.user import User


class Leaderboard(APIView):
    def get(self, request):
        users = (
            User.objects.filter(
                karma_activity_log__task__event="launchpad",
                karma_activity_log__appraiser_approved=True,
                karma_activity_log__task__hashtag="#lp24-introduction",
            )
            .annotate(
                karma=Sum("karma_activity_log__karma"),
                org=F("userorganizationlink__title"),
                district=F("district__name"),
                state=F("district__zone__state__name"),
                time_=Max("karma_activity_log__created_at"),
            )
            .order_by("-karma", "time_")
        )
        paginated_queryset = CommonUtils.get_paginated_queryset(
            users,
            request,
            ["karma", "org", "district", "state", "time_"],
            sort_fields={
                "karma": "karma",
                "org": "org",
                "district": "district",
                "state": "state",
                "time_": "time_",
            },
        )

        serializer = LaunchpadLeaderBoardSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse.paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )
