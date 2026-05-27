from django.urls import path

from api.dashboard.company.jobs.application_views import (
    LearnerApplicationsAPIView,
    LearnerWithdrawApplicationAPIView,
)

urlpatterns = [
    path("", LearnerApplicationsAPIView.as_view(), name="learner-applications"),
    path("<str:app_id>/withdraw/", LearnerWithdrawApplicationAPIView.as_view(), name="learner-application-withdraw"),
]
