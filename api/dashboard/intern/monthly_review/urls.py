from django.urls import path
from . import monthly_review_views

urlpatterns = [
    path("", monthly_review_views.InternMonthlyReviewAPI.as_view(), name="intern-monthly-review-list-create"),
    path("prefill/", monthly_review_views.InternMonthlyReviewPrefillAPI.as_view(), name="intern-monthly-review-prefill"),
    path("current/", monthly_review_views.InternMonthlyReviewCurrentAPI.as_view(), name="intern-monthly-review-current"),
    path("history/", monthly_review_views.InternMonthlyReviewHistoryAPI.as_view(), name="intern-monthly-review-history"),
    path("<str:review_id>/", monthly_review_views.InternMonthlyReviewAPI.as_view(), name="intern-monthly-review-detail"),
]
