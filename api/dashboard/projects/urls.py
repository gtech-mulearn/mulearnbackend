from django.urls import path

from . import projects_view


urlpatterns = [
    path("create/", projects_view.ProjectView.as_view()),
    path("delete/<str:id>/", projects_view.ProjectView.as_view()),
    path("edit/<str:id>/", projects_view.ProjectView.as_view()),
    path("projects/", projects_view.GetUserProjectView.as_view()),
    path("get/", projects_view.ProjectView.as_view()),
    path("upvote/<str:project_id>/", projects_view.AddProjectUpvoteView.as_view()),
]
