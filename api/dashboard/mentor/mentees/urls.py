from django.urls import path
from .mentee_views import MentorMenteeView

urlpatterns = [
    path("", MentorMenteeView.as_view(), name="mentor-mentees"),
]
