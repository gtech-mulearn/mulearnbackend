from django.urls import path
from .overview_views import MentorOverviewView

urlpatterns = [
    path("", MentorOverviewView.as_view(), name="mentor-overview"),
]
