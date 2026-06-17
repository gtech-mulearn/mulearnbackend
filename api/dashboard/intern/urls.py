from django.urls import path, include
from api.dashboard.intern.overview import overview_views

urlpatterns = [
    path("timesheets/", include("api.dashboard.intern.timesheet.urls")),
    path("reviews/", include("api.dashboard.intern.weekly_review.urls")),
    path("overview/", include("api.dashboard.intern.overview.urls")),
    path("leaderboard/", include("api.dashboard.intern.leaderboard.urls")),
    path("tasks/", include("api.dashboard.intern.tasks.urls")),
    path("leave/", include("api.dashboard.intern.leave.urls")),
    path("guilds/", overview_views.InternGuildsAPI.as_view(), name="intern-guilds"),
    path("minutes/", include("api.dashboard.intern.minutes.urls")),
]
