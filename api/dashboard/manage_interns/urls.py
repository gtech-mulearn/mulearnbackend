from django.urls import path, include
from . import interns_views

urlpatterns = [
    path("reviews/", include("api.dashboard.manage_interns.reviews.urls")),
    path("tasks/", include("api.dashboard.manage_interns.tasks.urls")),
    path("leave/", include("api.dashboard.manage_interns.leave.urls")),
    
    path("status/", interns_views.ManageInternStatusAPI.as_view(), name="manage-intern-status"),
    path("export/", interns_views.ManageInternExportAPI.as_view(), name="manage-intern-export"),
    path("", interns_views.ManageInternAPI.as_view(), name="manage-intern-list-create"),
    path("<str:intern_id>/", interns_views.ManageInternAPI.as_view(), name="manage-intern-update"),
]
