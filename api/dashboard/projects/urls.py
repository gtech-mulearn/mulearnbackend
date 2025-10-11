from django.urls import path

from . import projects_view

urlpatterns = [
    path('', projects_view.ProjectsAPIView.as_view()),
    path('<uuid:pk>/', projects_view.ProjectDetailAPIView.as_view()),
    path('vote/', projects_view.ProjectVoteAPI.as_view()),
    path('vote/<uuid:pk>/', projects_view.ProjectVoteAPI.as_view()),
    path('comment/', projects_view.ProjectCommentAPI.as_view()),
    path('comment/<uuid:pk>/', projects_view.ProjectCommentAPI.as_view()),
]