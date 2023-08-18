from django.urls import path

from . import location_views

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('countries/', location_views.CountryDataAPI.as_view()),
    path('countries/<str:country_id>/', location_views.CountryDataAPI.as_view()),
    
    path('states/', location_views.StateDataAPI.as_view()),
    path('states/<str:state_id>/', location_views.StateDataAPI.as_view()),
    
    path('zones/', location_views.ZoneDataAPI.as_view()),
    path('zones/<str:state_id>/', location_views.ZoneDataAPI.as_view()),
    
    path('districts/', location_views.DistrictDataAPI.as_view()),
    path('districts/<str:zone_id>/', location_views.DistrictDataAPI.as_view()),
]
