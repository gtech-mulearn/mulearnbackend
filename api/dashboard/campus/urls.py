from django.urls import path
from . import campus_views

urlpatterns = [
    path("student-details/", campus_views.StudentDetailsAPI.as_view()),
    path("student-details/csv/", campus_views.StudentDetailsCSVAPI.as_view()),
    path("campus-details/", campus_views.CampusDetailsAPI.as_view()),
    path("student-level/", campus_views.StudentInEachLevelAPI.as_view()),
]
