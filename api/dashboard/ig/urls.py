from django.urls import path

from . import dash_ig_view

urlpatterns = [
    path('', dash_ig_view.InterestGroupAPI.as_view()),
]
