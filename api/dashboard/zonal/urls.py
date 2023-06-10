from django.urls import path
from . import dash_zonal_views

urlpatterns = [
    path("student-details/", dash_zonal_views.ZonalStudentsAPI.as_view()),
    path("student-details/csv/", dash_zonal_views.ZonalStudentsCSV.as_view()),
    path("campus-details/", dash_zonal_views.ZonalCampusAPI.as_view()),
    path("campus-details/csv/", dash_zonal_views.ZonalCampusCSV.as_view()),
]
