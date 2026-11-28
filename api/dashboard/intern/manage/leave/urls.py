from django.urls import path
from . import leave_views

urlpatterns = [
    path("", leave_views.ManageInternLeaveAPI.as_view(), name="manage-intern-leave-list"),
    path("<str:leave_id>/", leave_views.ManageInternLeaveAPI.as_view(), name="manage-intern-leave-detail"),
    path("<str:leave_id>/review/", leave_views.ManageInternLeaveReviewAPI.as_view(), name="manage-intern-leave-review"),
]
