from django.urls import path

from . import location_views

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('countries/', location_views.CountryDataAPI.as_view()),
    path('countries/list/', location_views.CountryListApi.as_view()),
    path('countries/<str:country_id>/', location_views.CountryDataAPI.as_view()),
    
    path('states/', location_views.StateDataAPI.as_view()),
    path('states/list/', location_views.StateListApi.as_view()),
    path('states/<str:state_id>/', location_views.StateDataAPI.as_view()),
    
    path('zones/', location_views.ZoneDataAPI.as_view()),
    path('zones/list/', location_views.ZoneListApi.as_view()),
    path('zones/<str:zone_id>/', location_views.ZoneDataAPI.as_view()),
    
    path('districts/', location_views.DistrictDataAPI.as_view()),
    path('districts/<str:district_id>/', location_views.DistrictDataAPI.as_view()),
]
