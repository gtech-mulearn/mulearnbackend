from django.urls import path
from . import views

urlpatterns = [
    path('', views.TaskReportInfoView.as_view()),
    path('<str:report_id>/', views.TaskReportInfoView.as_view()),
    path('group-by-reporter/', views.TaskReportReporterGroupingView.as_view()),
]
