from django.urls import path
from .persona_views import PersonaSwitchView, PersonaResetView, IGRolesView

urlpatterns = [
    path("switch/", PersonaSwitchView.as_view(), name="mentor-persona-switch"),
    path("reset/", PersonaResetView.as_view(), name="mentor-persona-reset"),
    path("ig-roles/", IGRolesView.as_view(), name="mentor-ig-roles"),
]
