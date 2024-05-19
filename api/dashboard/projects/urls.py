from django.urls import path
from . import projects_view

urlpatterns = [
    path('',projects_view.ProjectsView.as_view(), name='project-list'),
    path('view/<int:projects_id>/',projects_view.ProjectsView.as_view(), name='project-list'),
    path('create/',projects_view.ProjectsView.as_view(), name='project-create'),
    path('edit/<int:projects_id>/',projects_view.ProjectsView.as_view(), name='project-edit'),
    path('delete/<int:projects_id>/',projects_view.ProjectsView.as_view(), name='project-delete'),
]
