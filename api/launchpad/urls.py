from django.urls import path

from . import launchpad_views

urlpatterns = [
    path('leaderboard/', launchpad_views.Leaderboard.as_view()),
    path('list-participants/', launchpad_views.ListParticipantsAPI.as_view()),
    path('launchpad-details/', launchpad_views.LaunchpadDetailsCount.as_view()),
    path('college-data/', launchpad_views.CollegeData.as_view())
]
