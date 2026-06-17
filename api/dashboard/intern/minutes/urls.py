from django.urls import path
from . import minutes_views

urlpatterns = [
    path("", minutes_views.InternGuildMinuteAPI.as_view(), name="intern-guild-minutes-list"),
    path("<str:minute_id>/", minutes_views.InternGuildMinuteAPI.as_view(), name="intern-guild-minutes-detail"),
]
