from django.urls import path
from . import campus_views

urlpatterns = [
    path("campus-details/", campus_views.CampusDetailsAPI.as_view()),
    path("student-level/", campus_views.CampusStudentInEachLevelAPI.as_view()),
    path("student-details/<str:url>/", campus_views.CampusStudentDetailsAPI.as_view()),
    path("student-details/<str:url>/csv/", campus_views.CampusStudentDetailsCSVAPI.as_view()),
]
