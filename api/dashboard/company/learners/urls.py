from django.urls import path

from .views import LearnerDiscoveryAPIView

urlpatterns = [
    path("", LearnerDiscoveryAPIView.as_view(), name="company-learner-discovery"),
]
