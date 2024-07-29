from django.urls import path

from . import launchpad_views

urlpatterns = [
    path('leaderboard/', launchpad_views.Leaderboard.as_view()),
    path('task-completed-leaderboard/', launchpad_views.TaskCompletedLeaderboard.as_view()),
    path('list-participants/', launchpad_views.ListParticipantsAPI.as_view()),
    path('launchpad-details/', launchpad_views.LaunchpadDetailsCount.as_view()),
    path('college-data/', launchpad_views.CollegeData.as_view()),
    path('user-college-link/', launchpad_views.LaunchPadUser.as_view()),
    path('user-college-link/<str:email>', launchpad_views.LaunchPadUser.as_view()),
    path('user-college-link-public/<str:email>', launchpad_views.LaunchPadUserPublic.as_view()),
    path('user-profile/', launchpad_views.UserProfile.as_view()),
    path('user-college-data/', launchpad_views.UserBasedCollegeData.as_view()),
    path('bulk-user-college-link/', launchpad_views.BulkLaunchpadUser.as_view()),
    path('list-participants-admin/', launchpad_views.LaunchPadListAdmin.as_view()),
    path('user-details/<str:launchpad_id>/', launchpad_views.UserProfileAPI.as_view()),
    path('socials/<str:launchpad_id>/', launchpad_views.GetSocialsAPI.as_view()),
    path('user-log/<str:launchpad_id>/', launchpad_views.UserLogAPI.as_view()),
    path('get-user-levels/<str:launchpad_id>/', launchpad_views.UserLevelsAPI.as_view()),
]
