from django.urls import path
from . import leadrboard_view

urlpatterns = [
    path('students/', leadrboard_view.StudentsLeaderboard.as_view()),
    path('students-monthly/', leadrboard_view.StudentsMonthlyLeaderboard.as_view()),
]
