from django.urls import path
from . import dash_lc_consumers

urlpatterns = [
    path("<str:lc_id>/chat/<str:room_name>/<str:user_id>/", dash_lc_consumers.LcChatConsumer.as_asgi())
]
