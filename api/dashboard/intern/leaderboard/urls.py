from django.urls import path
from . import leaderboard_views

urlpatterns = [
    path("", leaderboard_views.InternLeaderboardAPI.as_view(), name="intern-leaderboard"),
    path("me/", leaderboard_views.InternLeaderboardMeAPI.as_view(), name="intern-leaderboard-me"),
]
