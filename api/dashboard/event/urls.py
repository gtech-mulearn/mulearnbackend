from django.urls import path
from .event_views import EventAPI, EventVerificationAPI

urlpatterns = [
    path("", EventAPI.as_view()),
    path("create/", EventAPI.as_view()),
    path("edit/<str:event_id>/", EventAPI.as_view()),
    path("verify/<str:event_id>/", EventVerificationAPI.as_view()),
    path("<str:event_id>/", EventAPI.as_view()),
]
