from django.urls import path
from . import mentorship_views

urlpatterns = [
    path("status/", mentorship_views.MentorStatusAPI.as_view(), name="mentor-status"),
    path("profile/", mentorship_views.MentorProfileAPI.as_view(), name="mentor-profile"),
    path("sessions/", mentorship_views.MentorSessionAPI.as_view(), name="mentor-sessions"),
    path("sessions/<str:session_id>/", mentorship_views.MentorSessionAPI.as_view(), name="mentor-session-detail"),
    path("mentees/", mentorship_views.MentorMenteeAPI.as_view(), name="mentor-mentees"),
    path("tasks/queue/", mentorship_views.MentorTaskQueueAPI.as_view(), name="mentor-task-queue"),
    path("tasks/queue/<str:log_id>/", mentorship_views.MentorTaskQueueAPI.as_view(), name="mentor-task-action"),
]
