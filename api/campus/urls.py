from django.urls import path

from api.campus.campus_views import CampusDetails, StudentDetails

urlpatterns = [
    path("student-details/", StudentDetails.as_view()),
    path("campus-details/", CampusDetails.as_view()),
]