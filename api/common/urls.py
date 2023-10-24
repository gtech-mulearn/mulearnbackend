from django.urls import path

from . import common_views

urlpatterns = [
    path('lc-dashboard/', common_views.LcDashboardAPI.as_view()),
    path('lc-report/', common_views.LcReportAPI.as_view()),
    path('college-wise-lc-report/', common_views.CollegeWiseLcReport.as_view()),
    path('download/lc-report/', common_views.LcReportDownloadAPI.as_view()),
    path('global-count/', common_views.GlobalCountAPI.as_view()),
    path('gta-sandshore/',common_views.GTASANDSHOREAPI.as_view())
]
