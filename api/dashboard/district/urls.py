from django.urls import path

from . import dash_district_views

urlpatterns = [
    path('district-details/', dash_district_views.DistrictDetailAPI.as_view(), name='district-details'),
    path('top-campus/', dash_district_views.DistrictTopThreeCampusAPI.as_view(), name='top-3-campuses'),
    path('college-level/', dash_district_views.DistrictStudentLevelStatusAPI.as_view(), name='student-level-status'),
    path("student-details/", dash_district_views.DistrictStudentDetailsAPI.as_view()),
    path("student-details/csv/", dash_district_views.DistrictStudentDetailsCSVAPI.as_view()),
    path("college-list/", dash_district_views.ListAllDistrictsAPI.as_view(), name='list-all-colleges'),
    path("college-list/csv/", dash_district_views.ListAllDistrictsCSVAPI.as_view(), name='list-all-college-csv'),
]
