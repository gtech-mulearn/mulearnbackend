from django.urls import path

from . import launchpad_views

urlpatterns = [
    path('leaderboard/', launchpad_views.Leaderboard.as_view()),
]