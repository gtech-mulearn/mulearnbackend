from django.urls import path

from . import channel_views

urlpatterns = [
    path('',channel_views.ChannelGetView.as_view()),
    path('create/',channel_views.ChannelAddView.as_view()),
    path('edit/<str:channel_id>/',channel_views.ChannelEditView.as_view()),
    path('delete/<str:channel_id>/',channel_views.ChannelDeleteView.as_view())
]
