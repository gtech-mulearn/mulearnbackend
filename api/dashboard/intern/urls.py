from django.urls import path, include
from api.dashboard.intern.team import team_views

urlpatterns = [
    path("timesheets/", include("api.dashboard.intern.timesheet.urls")),
    path("reviews/", include("api.dashboard.intern.weekly_review.urls")),
    path("monthly-reviews/", include("api.dashboard.intern.monthly_review.urls")),
    path("overview/", include("api.dashboard.intern.overview.urls")),
    path("leaderboard/", include("api.dashboard.intern.leaderboard.urls")),
    path("tasks/", include("api.dashboard.intern.tasks.urls")),
    path("leave/", include("api.dashboard.intern.leave.urls")),
    path("team/", include("api.dashboard.intern.team.urls")),
    path("teams/", team_views.InternTeamListAPI.as_view(), name="intern-teams"),
    path("minutes/", include("api.dashboard.intern.minutes.urls")),
]
