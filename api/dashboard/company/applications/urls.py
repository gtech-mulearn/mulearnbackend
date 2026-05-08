from django.urls import path

from api.dashboard.company.jobs.application_views import LearnerApplicationsAPIView

urlpatterns = [
    path("", LearnerApplicationsAPIView.as_view(), name="learner-applications"),
]
