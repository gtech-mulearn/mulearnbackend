from django.urls import path

from . import location_views

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('country/', location_views.CountryDataAPI.as_view()),
    path('country/<str:country_id>/', location_views.CountryDataAPI.as_view()),
    
    path('state/', location_views.StateDataAPI.as_view()),
    path('state/<str:country_id>/', location_views.StateDataAPI.as_view()),
    
    path('zone/', location_views.ZoneDataAPI.as_view()),
    path('zone/<str:state_id>/', location_views.ZoneDataAPI.as_view()),
    
    path('district/', location_views.DistrictDataAPI.as_view()),
    path('district/<str:zone_id>/', location_views.DistrictDataAPI.as_view()),
]
