from django.urls import path

from building_blocks.health import views

urlpatterns = [
    path("live", views.live, name="healthz-live"),
    path("ready", views.ready, name="healthz-ready"),
]
