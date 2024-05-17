from django.urls import path
from . import projects_view


urlpatterns = [
    path('', projects_view.ProjectsCRUDAPI.as_view()),
]
