from django.urls import path
from . import notification_view

urlpatterns = [
    path('list/', notification_view.NotificationListsAPI.as_view(), name='list-notification'),
    path('delete/<str:notification_id>/', notification_view.NotificationDeleteAPI.as_view(),
         name='delete-notification'),
    ]