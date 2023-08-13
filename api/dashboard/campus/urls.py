from django.urls import path

from . import campus_views

urlpatterns = [
    path("campus-details/", campus_views.CampusDetailsAPI.as_view()),
    path("student-level/", campus_views.CampusStudentInEachLevelAPI.as_view()),
    path("student-details/", campus_views.CampusStudentDetailsAPI.as_view()),
    path("student-details/csv/", campus_views.CampusStudentDetailsCSVAPI.as_view()),
    path("weekly-karma/", campus_views.WeeklyKarmaAPI.as_view()),
]
