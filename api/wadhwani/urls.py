from django.urls import path

from . import wadhwani_views

urlpatterns = [
    path('college/', wadhwani_views.WadhwaniCollegeLeaderboard.as_view()),
    path('zonal/', wadhwani_views.WadhwaniZonalLeaderboard.as_view()),
    
]