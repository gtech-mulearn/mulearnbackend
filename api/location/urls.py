from django.urls import path, include
from . import location_views

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('country', location_views.CountryData.as_view()),
    path('<str:country>/states', location_views.StateData.as_view()),
    path('<str:country>/<str:state>/zone', location_views.ZoneData.as_view()),
    path('<str:country>/<str:state>/<str:zone>/district', location_views.DistrictData.as_view()),
]
