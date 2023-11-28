from django.urls import path

from . import campus_views

urlpatterns = [
    path("campus-details/", campus_views.CampusDetailsAPI.as_view(), name='campus-details'),
    path("student-level/", campus_views.CampusStudentInEachLevelAPI.as_view(), name='student-in-each-level'),
    path("student-details/", campus_views.CampusStudentDetailsAPI.as_view(), name='student-details'),
    path("student-details/csv/", campus_views.CampusStudentDetailsCSVAPI.as_view(), name='student-details-csv'),
    path("weekly-karma/", campus_views.WeeklyKarmaAPI.as_view(), name='weekly-karma-insights'),

    path('change-student-type/<str:member_id>/', campus_views.ChangeStudentTypeAPI.as_view(), name='change-student-type')
]
