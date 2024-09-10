from django.urls import path
from .event_views import (
    MuEventsAPI,
    MuEventsVerificationAPI,
    MuEventKarmaRequestAPI,
    MuEventKarmaRequestVerificationAPI,
)

urlpatterns = [
    path("", MuEventsAPI.as_view()),
    path("create/", MuEventsAPI.as_view()),
    path("event/<str:event_id>/", MuEventsAPI.as_view()),
    path("event/<str:event_id>/edit/", MuEventsAPI.as_view()),
    path("event/<str:event_id>/verify/", MuEventsVerificationAPI.as_view()),
    path("event/<str:event_id>/request/", MuEventKarmaRequestAPI.as_view()),
    path(
        "event/<str:event_id>/request/<str:karma_request_id>/edit/",
        MuEventKarmaRequestAPI.as_view(),
    ),
    path(
        "event/<str:event_id>/request/<str:karma_request_id>/verify/",
        MuEventKarmaRequestVerificationAPI.as_view(),
    ),
]
