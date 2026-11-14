from django.urls import path

from . import views

urlpatterns = [
    # Called by the media worker's scheduled cleanup (Api-Key header).
    path("unreferenced-keys/", views.UnreferencedMediaKeysAPI.as_view()),
]
