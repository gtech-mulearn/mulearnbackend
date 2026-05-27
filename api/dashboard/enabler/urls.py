from django.urls import path
from . import enabler_views

urlpatterns = [
    path("home-summary/", enabler_views.EnablerHomeSummaryAPI.as_view(), name="enabler-home-summary"),
    path("campuses/", enabler_views.EnablerCampusListAPI.as_view(), name="enabler-campuses"),
    path("campuses/<str:campus_id>/review/", enabler_views.EnablerCampusReviewAPI.as_view(), name="enabler-campus-review"),
    path("campuses/<str:campus_id>/notes/", enabler_views.EnablerCampusNoteAPI.as_view(), name="enabler-campus-notes"),
    path("reports/", enabler_views.EnablerReportsAPI.as_view(), name="enabler-reports"),
]
