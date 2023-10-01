from django.urls import path

from . import leaderboard_view

urlpatterns = [
    path('students/', leaderboard_view.StudentsLeaderboard.as_view()),
    path('students-monthly/', leaderboard_view.StudentsMonthlyLeaderboard.as_view()),
    path('college/', leaderboard_view.CollegeLeaderboard.as_view()),
    path('college-monthly/', leaderboard_view.CollegeMonthlyLeaderboard.as_view())
]
