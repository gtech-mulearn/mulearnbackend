from django.urls import path

from api.campus.campus_views import StudentDetails

urlpatterns = [
    path("student-details/", StudentDetails.as_view()),
]