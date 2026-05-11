from django.urls import path
from .task_views import MentorTaskQueueView, MentorTaskActionView
from .task_request_views import MentorTaskRequestView

urlpatterns = [
    # Task review queue (mentor reviews mentee submissions)
    path("queue/",             MentorTaskQueueView.as_view(),  name="mentor-task-queue"),
    path("queue/<str:log_id>/", MentorTaskActionView.as_view(), name="mentor-task-action"),

    # Task creation requests (mentor → admin)
    path("requests/", MentorTaskRequestView.as_view(), name="mentor-task-request"),
]
