from django.urls import path
from . import review_views

urlpatterns = [
    path("timesheets/<str:timesheet_id>/review/", review_views.InternTimesheetReviewAPI.as_view(), name="intern-timesheet-review"),
    path("reviews/<str:review_id>/review/", review_views.InternWeeklyReviewReviewAPI.as_view(), name="intern-weekly-review-review"),
    path("monthly/<str:review_id>/review/", review_views.InternMonthlyReviewReviewAPI.as_view(), name="intern-monthly-review-review"),
    path("monthly/missing/", review_views.InternMonthlyReviewMissingAPI.as_view(), name="intern-monthly-review-missing"),
    path("monthly/missing/export/", review_views.InternMonthlyReviewMissingExportAPI.as_view(), name="intern-monthly-review-missing-export"),
    path("timesheets/missing/export/", review_views.InternTimesheetMissingExportAPI.as_view(), name="intern-timesheet-missing-export"),
    path("timesheets/missing/", review_views.InternTimesheetMissingAPI.as_view(), name="intern-timesheet-missing"),
    path("monthly/", review_views.InternMonthlyReviewListAPI.as_view(), name="intern-monthly-review-list"),
    
    path("timesheets/", review_views.InternTimesheetListAPI.as_view(), name="intern-timesheet-list"),
    path("", review_views.InternWeeklyReviewListAPI.as_view(), name="intern-weekly-review-list"),
]
