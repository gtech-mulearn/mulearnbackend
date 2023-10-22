from django.urls import path

from . import channel_views

urlpatterns = [
    path("", channel_views.ChannelCRUDAPI.as_view()),
    path("create/", channel_views.ChannelCRUDAPI.as_view()),
    path("edit/<str:affliation_id>/", channel_views.ChannelCRUDAPI.as_view()),
    path("delete/<str:affliation_id>/", channel_views.ChannelCRUDAPI.as_view()),
    
]