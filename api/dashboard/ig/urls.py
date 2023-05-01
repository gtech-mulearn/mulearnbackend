from django.urls import path
from . import ig_view

urlpatterns = [
    path('', ig_view.InterestGroupAPI.as_view(),name="ig-api")
]
