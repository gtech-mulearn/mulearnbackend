from django.urls import path, include
from . import interns_views

urlpatterns = [
    path("reviews/", include("api.dashboard.manage_interns.reviews.urls")),
    path("tasks/", include("api.dashboard.manage_interns.tasks.urls")),
    path("leave/", include("api.dashboard.manage_interns.leave.urls")),
    
    path("status/", interns_views.ManageInternStatusAPI.as_view(), name="manage-intern-status"),
    path("interns/export/", interns_views.ManageInternExportAPI.as_view(), name="manage-intern-export"),
    path("interns/import/template/", interns_views.ManageInternBulkImportTemplateAPIView.as_view(), name="manage-intern-bulk-import-template"),
    path("interns/import/", interns_views.ManageInternBulkImportAPI.as_view(), name="manage-intern-bulk-import"),
    path("interns/", interns_views.ManageInternAPI.as_view(), name="manage-intern-list-create"),
    path("interns/<str:intern_id>/", interns_views.ManageInternAPI.as_view(), name="manage-intern-update-delete"),
]
