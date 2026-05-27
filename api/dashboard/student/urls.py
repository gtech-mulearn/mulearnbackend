from django.urls import path

from . import student_views

urlpatterns = [
    path(
        "participation-breakdown/",
        student_views.StudentParticipationBreakdownAPI.as_view(),
        name="participation-breakdown",
    ),
]
