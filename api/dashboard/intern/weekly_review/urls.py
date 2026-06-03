from django.urls import path
from . import weekly_review_views

urlpatterns = [
    path("", weekly_review_views.InternWeeklyReviewAPI.as_view(), name="intern-weekly-review-list-create"),
    path("current/", weekly_review_views.InternWeeklyReviewCurrentAPI.as_view(), name="intern-weekly-review-current"),
    path("history/", weekly_review_views.InternWeeklyReviewHistoryAPI.as_view(), name="intern-weekly-review-history"),
    path("<str:review_id>/", weekly_review_views.InternWeeklyReviewAPI.as_view(), name="intern-weekly-review-edit"),
]
