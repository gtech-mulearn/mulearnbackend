from django.urls import path
from . import review_views

urlpatterns = [
    path("timesheets/<str:timesheet_id>/review/", review_views.InternTimesheetReviewAPI.as_view(), name="intern-timesheet-review"),
    path("reviews/<str:review_id>/review/", review_views.InternWeeklyReviewReviewAPI.as_view(), name="intern-weekly-review-review"),
]
