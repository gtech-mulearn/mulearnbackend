from django.urls import path
from .project_views import ProjectCRUDAPI

urlpatterns = [
    path("", ProjectCRUDAPI.as_view(), name='project-list'),
    path("create/", ProjectCRUDAPI.as_view(), name='project-create'),
    path("edit/<str:project_id>/", ProjectCRUDAPI.as_view(), name='project-edit'),
    path("delete/<str:project_id>/", ProjectCRUDAPI.as_view(), name='project-delete'),
]
