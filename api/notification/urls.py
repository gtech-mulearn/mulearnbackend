from django.urls import path

from . import notification_view

urlpatterns = [
    path('list/', notification_view.NotificationListsAPI.as_view(), name='list-notification'),
    path('delete/id/<str:notification_id>/', notification_view.NotificationDeleteAPI.as_view(),
         name='delete-notification'),
    path('delete/all/', notification_view.NotificationDeleteAllAPI.as_view(), name='delete-all-notification'),
]
