from django.urls import path
from .availability_views import MentorAvailabilityView, MentorAvailabilitySlotDeleteView

urlpatterns = [
    path("", MentorAvailabilityView.as_view(), name="mentor-availability"),
    path("<str:slot_id>/", MentorAvailabilitySlotDeleteView.as_view(), name="mentor-availability-delete"),
]
