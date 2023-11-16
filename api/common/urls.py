from django.urls import path

from . import common_views

urlpatterns = [
    path('lc-dashboard/', common_views.LcDashboardAPI.as_view()),
    path('lc-report/', common_views.LcReportAPI.as_view()),
    path('college-wise-lc-report/', common_views.CollegeWiseLcReport.as_view()),
    path('college-wise-lc-report/csv/', common_views.CollegeWiseLcReportCSV.as_view()),
    path('lc-report/csv/', common_views.LcReportDownloadAPI.as_view()),
    path('global-count/', common_views.GlobalCountAPI.as_view()),
    path('gta-sandshore/', common_views.GTASANDSHOREAPI.as_view()),
    path('profile-pic/<str:muid>/', common_views.UserProfilePicAPI.as_view()),
    path('list-ig/', common_views.ListIGAPI.as_view()),
    path('list-ig-top100/', common_views.ListTopIgUsersAPI.as_view()),
]
