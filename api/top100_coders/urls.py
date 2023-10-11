from django.urls import path

from . import top100_view

urlpatterns = [
    path('leaderboard/', top100_view.Leaderboard.as_view()),
]