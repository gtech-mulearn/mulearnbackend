from django.urls import path

from .views import LearnerDashboardSummaryAPIView, LearnerStreakAPIView


urlpatterns = [
    path("learner/summary/", LearnerDashboardSummaryAPIView.as_view(), name="learner-home-summary"),
    path("learner/streak/", LearnerStreakAPIView.as_view(), name="learner-streak"),
]
