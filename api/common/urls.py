from django.urls import path

from . import common_views

urlpatterns = [
    path('lc-dashboard/', common_views.LcDashboardAPI.as_view()),
    path('lc-report/', common_views.LcReportAPI.as_view()),
    path('<str:log_type>/', common_views.CommonAPI.as_view(), name='common-log-download'),

]
