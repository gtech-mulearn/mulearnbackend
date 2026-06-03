from django.urls import path, include

urlpatterns = [
    path("timesheets/", include("api.dashboard.intern.timesheet.urls")),
    path("reviews/", include("api.dashboard.intern.weekly_review.urls")),
    path("overview/", include("api.dashboard.intern.overview.urls")),
    path("leaderboard/", include("api.dashboard.intern.leaderboard.urls")),
    path("tasks/", include("api.dashboard.intern.tasks.urls")),
    path("leave/", include("api.dashboard.intern.leave.urls")),
]
