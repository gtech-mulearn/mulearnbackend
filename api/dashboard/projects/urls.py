from django.urls import path

from . import projects_view

urlpatterns = [
    path('', projects_view.ProjectListView.as_view(), name='list_all_project'),
    path('<int:project_id>/', projects_view.ProjectListView.as_view(), name='list_project'),
    path('create/', projects_view.ProjectCreateView.as_view(), name='create_project'),
    path('edit/<int:project_id>/', projects_view.ProjectUpdateView.as_view(), name='edit_project'),
    path('delete/<int:project_id>/', projects_view.ProjectDeleteView.as_view(), name='delete_project'),
]
