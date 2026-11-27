from django.urls import path

from . import team_views

urlpatterns = [
    path("members/", team_views.InternTeamMembersAPI.as_view(), name="intern-team-members"),
]
