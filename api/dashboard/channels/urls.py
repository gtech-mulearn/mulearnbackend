from django.urls import path

from . import channel_views

urlpatterns = [
    path('',channel_views.ChannelView.as_view()),
    path('create/',channel_views.ChannelView.as_view()),
    path('edit/<str:channel_id>/',channel_views.ChannelView.as_view()),
    path('delete/<str:channel_id>/',channel_views.ChannelView.as_view())
]
