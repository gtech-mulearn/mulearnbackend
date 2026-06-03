from django.urls import path
from . import timesheet_views

urlpatterns = [
    path("", timesheet_views.InternTimesheetAPI.as_view(), name="intern-timesheet-list-create"),
    path("today/", timesheet_views.InternTimesheetTodayAPI.as_view(), name="intern-timesheet-today"),
    path("history/", timesheet_views.InternTimesheetHistoryAPI.as_view(), name="intern-timesheet-history"),
    path("summary/", timesheet_views.InternTimesheetSummaryAPI.as_view(), name="intern-timesheet-summary"),
    path("<str:timesheet_id>/", timesheet_views.InternTimesheetAPI.as_view(), name="intern-timesheet-edit"),
]
