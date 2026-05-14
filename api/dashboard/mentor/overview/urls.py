from django.urls import path
from .overview_views import MentorHomeSummaryView, MentorOverviewView

urlpatterns = [
    path("", MentorOverviewView.as_view(), name="mentor-overview"),
    path("home-summary/", MentorHomeSummaryView.as_view(), name="mentor-home-summary"),
]
