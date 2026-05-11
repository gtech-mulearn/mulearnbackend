from django.urls import path
from .session_views import MentorSessionView, MentorSessionDetailView

urlpatterns = [
    path("", MentorSessionView.as_view(), name="mentor-sessions"),
    path("<str:session_id>/", MentorSessionDetailView.as_view(), name="mentor-session-detail"),
]
