from django.urls import path

from .common_views import *
from .external_api_views import ExternalUserDetailsAPI
from . import common_views
from . import college_details_views

urlpatterns = [
    path('campus-details/<str:college_code>/', college_details_views.CollegeDetailsAPI.as_view()),
    path('lc-list', common_views.LcListAPI.as_view()),
    path('<str:circle_id>/lc-details/', common_views.LcDetailsAPI.as_view()),
    path('lc-dashboard/', common_views.LcDashboardAPI.as_view()),
    path('lc-report/', common_views.LcReportAPI.as_view()),
    path('college-wise-lc-report/', common_views.CollegeWiseLcReport.as_view()),
    path('college-wise-lc-report/csv/', common_views.CollegeWiseLcReportCSV.as_view()),
    path('lc-report/csv/', common_views.LcReportDownloadAPI.as_view()),
    path('lc-enrollment/', common_views.LearningCircleEnrollment.as_view()),
    path('lc-enrollment/csv/', common_views.LearningCircleEnrollmentCSV.as_view()),

    path('global-count/', common_views.GlobalCountAPI.as_view()),

    path('gta-sandshore/', common_views.GTASANDSHOREAPI.as_view()),
    path('profile-pic/<str:muid>/', common_views.UserProfilePicAPI.as_view()),
    path('list-ig/', common_views.ListIGAPI.as_view()),
    path('list-ig-top100/', common_views.ListTopIgUsersAPI.as_view()),
    path("list/levels/", common_views.ListAllLevelInfo.as_view()),

    path('leaderboard/top-100/', common_views.BekenAPI.as_view()),

    
    path("list/college/", common_views.LcCollegeAPI.as_view()),
    path("list/district/", common_views.LcDistrictAPI.as_view()),
    path("list/state/", common_views.LcStateAPI.as_view()),
    path("list/country/", common_views.LcCountryAPI.as_view()),
    path("external/user/", ExternalUserDetailsAPI.as_view()),
]
