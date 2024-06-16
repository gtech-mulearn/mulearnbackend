from django.urls import path

from . import launchpad_views

urlpatterns = [
    path('leaderboard/', launchpad_views.Leaderboard.as_view()),
    path('list-participants/', launchpad_views.ListParticipantsAPI.as_view()),
    path('launchpad-details/', launchpad_views.LaunchpadDetailsCount.as_view()),
    path('college-data/', launchpad_views.CollegeData.as_view()),
    path('user-college-link/', launchpad_views.LaunchPadUser.as_view()),
    path('user-profile/', launchpad_views.UserProfile.as_view()),
    path('user-college-data/', launchpad_views.UserBasedCollegeData.as_view()),
    path('bulk-user-college-link/', launchpad_views.BulkLaunchpadUser.as_view()),
]
