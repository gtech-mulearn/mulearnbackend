from django.urls import path

from . import channel_views

urlpatterns = [
    path("", channel_views.ChannelCRUDAPI.as_view()),
    path("<str:channel_id>/", channel_views.ChannelCRUDAPI.as_view()),
    
]