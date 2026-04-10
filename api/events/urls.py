from django.urls import path

from . import views

urlpatterns = [
    path(
        "",
        views.EventListCreateAPI.as_view(),
        name="events-list-create",
    ),
    path(
        "<str:event_id>/",
        views.EventDetailAPI.as_view(),
        name="events-detail",
    ),
]
