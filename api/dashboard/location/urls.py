from django.urls import path
from . import location_views

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('country', location_views.CountryDataAPI.as_view()),
    path('<str:country>/states', location_views.StateDataAPI.as_view()),
    path('<str:country>/<str:state>/zone', location_views.ZoneDataAPI.as_view()),
    path('<str:country>/<str:state>/<str:zone>/district', location_views.DistrictDataAPI.as_view()),
]
