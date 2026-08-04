from django.urls import path
from .feature_views import GritMeterToggleAPI

urlpatterns = [
    path("grit-meter/", GritMeterToggleAPI.as_view()),
]
