from django.urls import path

from .feature_views import FeatureFlagAPI

urlpatterns = [
    # grit-meter/ keeps its URL; every flag in flags.FLAGS lives here.
    path("<slug:slug>/", FeatureFlagAPI.as_view()),
]
