from django.urls import path

from . import wadhwani_views

urlpatterns = [
    path('students/', wadhwani_views.WadhwaniStudentsLeaderboard.as_view()),
    path('college/', wadhwani_views.WadhwaniCollegeLeaderboard.as_view()),
    
]