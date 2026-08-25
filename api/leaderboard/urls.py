from django.urls import path

from . import leaderboard_view

urlpatterns = [
    path('students/', leaderboard_view.StudentsLeaderboard.as_view()),
    path('students-monthly/', leaderboard_view.StudentsMonthlyLeaderboard.as_view()),
    path('college/', leaderboard_view.CollegeLeaderboard.as_view()),
    path('college-monthly/', leaderboard_view.CollegeMonthlyLeaderboard.as_view()),
    path('wadhwani-college/', leaderboard_view.WadhwaniCollegeLeaderboard.as_view()),
    path('wadhwani-zonal/', leaderboard_view.WadhwaniZonalLeaderboard.as_view()),
    path('ig-mentor/<str:ig_id>/', leaderboard_view.IGMentorLeaderboard.as_view()),
    path('campus-mentor/<str:campus_id>/', leaderboard_view.CampusMentorLeaderboard.as_view()),
    path('company-mentor/<str:company_id>/', leaderboard_view.CompanyMentorLeaderboard.as_view()),
]
