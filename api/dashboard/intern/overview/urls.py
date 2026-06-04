from django.urls import path
from . import overview_views

urlpatterns = [
    path("status/", overview_views.InternOverviewStatusAPI.as_view(), name="intern-overview-status"),
    path("activity/", overview_views.InternOverviewActivityAPI.as_view(), name="intern-overview-activity"),
    path("leaderboard/top/", overview_views.InternOverviewLeaderboardTopAPI.as_view(), name="intern-overview-leaderboard-top"),
]
