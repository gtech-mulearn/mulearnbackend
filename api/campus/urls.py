from django.urls import path

from api.campus import campus_views

urlpatterns = [
    path("student-details/", campus_views.StudentDetails.as_view()),
    path("student-details/csv/", campus_views.StudentDetailsCSV.as_view()),
    path("campus-details/", campus_views.CampusDetails.as_view()),
]
