from django.urls import path

from . import teams_views

urlpatterns = [
    path("", teams_views.InternTeamAPI.as_view(), name="manage-intern-team-list-create"),
    path("<str:team_id>/activate/", teams_views.InternTeamActivateAPI.as_view(), name="manage-intern-team-activate"),
    path("<str:team_id>/", teams_views.InternTeamAPI.as_view(), name="manage-intern-team-detail"),
]
