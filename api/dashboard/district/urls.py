from django.urls import path
from . import dash_district_views

urlpatterns = [
    # path("student-details/", dash_district_views.DistrictStudentsAPI.as_view()),
    # path("student-details/csv/", dash_district_views.DistrictStudentsCSV.as_view()),
    # path("campus-details/", dash_district_views.DistrictCampusAPI.as_view()),
    # path("campus-details/csv/", dash_district_views.DistrictCampusCSV.as_view()),
    path('district-details/', dash_district_views.DistrictDetailAPI.as_view()),
    path('top-campus/', dash_district_views.DistrictTopThreeCampusAPI.as_view()),
    path('college-level/', dash_district_views.DistrictStudentLevelStatusAPI.as_view()),
    path("student-details/<str:url>/", dash_district_views.DistrictStudentDetailsAPI.as_view()),
    path("student-details/<str:url>/csv/", dash_district_views.DistrictStudentDetailsCSVAPI.as_view()),
]
