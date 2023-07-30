from django.urls import path
from . import dash_zonal_views

urlpatterns = [
    # path("student-details/", dash_zonal_views.ZonalStudentsAPI.as_view()),
    # path("student-details/csv/", dash_zonal_views.ZonalStudentsCSV.as_view()),
    # path("campus-details/", dash_zonal_views.ZonalCampusAPI.as_view()),
    # path("campus-details/csv/", dash_zonal_views.ZonalCampusCSV.as_view()),
    path("zonal-details/", dash_zonal_views.ZonalDetailsAPI.as_view()),
    path("top-districts/", dash_zonal_views.ZonalTopThreeDistrictAPI.as_view()),
    path("student-level/", dash_zonal_views.ZonalStudentLevelStatusAPI.as_view()),
    path("student-details/<str:url>/", dash_zonal_views.ZonalStudentDetailsAPI.as_view()),
    path("student-details/<str:url>/csv/", dash_zonal_views.ZonalStudentDetailsCSVAPI.as_view()),
]
