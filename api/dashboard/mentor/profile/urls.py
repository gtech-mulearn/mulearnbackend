from django.urls import path
from .profile_views import MentorProfileView

urlpatterns = [
    path("", MentorProfileView.as_view(), name="mentor-profile"),
]
