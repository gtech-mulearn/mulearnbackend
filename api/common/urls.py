from django.urls import path

from . import common_views

urlpatterns = [
    path('lc-dashboard/', common_views.LcDashboardAPI.as_view()),
    path('lc-report/', common_views.LcReportAPI.as_view()),
    path('download/lc-report/', common_views.LcReportDownloadAPI.as_view()),
]
