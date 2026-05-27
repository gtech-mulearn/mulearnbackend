from django.urls import path

from . import karma_views

urlpatterns = [
    path("histogram/", karma_views.KarmaHistogramAPI.as_view(), name="karma-histogram"),
]
