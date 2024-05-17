from django.urls import path
from . import projects_view


urlpatterns = [
    path('', projects_view.ProjectsCRUDAPI.as_view()),
    path('create/',projects_view.ProjectsCRUDAPI.as_view()),
    path('edit/<project_id>/', projects_view.ProjectsCRUDAPI.as_view()),
    path('delete/<project_id>/', projects_view.ProjectsCRUDAPI.as_view()),
]
