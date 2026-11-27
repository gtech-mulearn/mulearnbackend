from django.urls import path, include
from . import interns_views

urlpatterns = [
    path("reviews/", include("api.dashboard.intern.manage.reviews.urls")),
    path("tasks/", include("api.dashboard.intern.manage.tasks.urls")),
    path("leave/", include("api.dashboard.intern.manage.leave.urls")),
    path("teams/", include("api.dashboard.intern.manage.teams.urls")),
    
    path("status/", interns_views.ManageInternStatusAPI.as_view(), name="manage-intern-status"),
    path("interns/export/", interns_views.ManageInternExportAPI.as_view(), name="manage-intern-export"),
    path("interns/import/template/", interns_views.ManageInternBulkImportTemplateAPIView.as_view(), name="manage-intern-bulk-import-template"),
    path("interns/import/", interns_views.ManageInternBulkImportAPI.as_view(), name="manage-intern-bulk-import"),
    path("interns/reassign/", interns_views.ManageInternReassignAPI.as_view(), name="manage-intern-reassign"),
    path("interns/", interns_views.ManageInternAPI.as_view(), name="manage-intern-list-create"),
    path("interns/<str:user_id>/", interns_views.ManageInternAPI.as_view(), name="manage-intern-detail-update-delete"),
]
