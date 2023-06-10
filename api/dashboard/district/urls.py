from django.urls import path
from . import dash_district_views

urlpatterns = [
    path("student-details/", dash_district_views.DistrictStudentsAPI.as_view()),
    path("student-details/csv/", dash_district_views.DistrictStudentsCSV.as_view()),
    path("campus-details/", dash_district_views.DistrictCampusAPI.as_view()),
    path("campus-details/csv/", dash_district_views.DistrictCampusCSV.as_view()),
]
