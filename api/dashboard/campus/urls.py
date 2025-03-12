from django.urls import path

from . import campus_views

urlpatterns = [
    path("campus-details/", campus_views.CampusDetailsAPI.as_view(), name='campus-details'),
    path("student-level/", campus_views.CampusStudentInEachLevelAPI.as_view(), name='student-in-each-level'),
    path("student-details/", campus_views.CampusStudentDetailsAPI.as_view(), name='student-details'),
    path("student-details/csv/", campus_views.CampusStudentDetailsCSVAPI.as_view(), name='student-details-csv'),
    path("weekly-karma/", campus_views.WeeklyKarmaAPI.as_view(), name='weekly-karma-insights'),

    path('change-student-type/<str:member_id>/', campus_views.ChangeStudentTypeAPI.as_view(), name='change-student-type'),
    path('transfer-lead-role/', campus_views.TransferLeadRoleAPI.as_view(), name='transfer-lead-role'),
    path('transfer-enabler-role/', campus_views.TransferEnablerRoleAPI.as_view(), name='transfer-enabler-role'),
    path('transfer-ig-role/', campus_views.TransferIGRoleAPI.as_view(), name='transfer-lead-role'),
]
