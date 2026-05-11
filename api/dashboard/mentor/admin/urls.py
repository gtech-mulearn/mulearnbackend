from django.urls import path
from .admin_views import (
    AdminTaskRequestListView,
    AdminTaskRequestActionView,
    AdminMentorTierView,
)

urlpatterns = [
    # Task request queue
    path("task-requests/",             AdminTaskRequestListView.as_view(),   name="admin-task-request-list"),
    path("task-requests/<str:req_id>/", AdminTaskRequestActionView.as_view(), name="admin-task-request-action"),

    # Mentor tier management
    path("tier/<str:mentor_profile_id>/", AdminMentorTierView.as_view(), name="admin-mentor-tier"),
]
