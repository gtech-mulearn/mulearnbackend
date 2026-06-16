from django.urls import path

from . import notification_view

urlpatterns = [
    path('list/', notification_view.NotificationListsAPI.as_view(), name='list-notification'),
    path('delete/id/<str:notification_id>/', notification_view.NotificationDeleteAPI.as_view(),
         name='delete-notification'),
    path('delete/all/', notification_view.NotificationDeleteAllAPI.as_view(), name='delete-all-notification'),
    # Broadcast — delete (admin only)
    path('broadcast/delete/id/<str:broadcast_id>/', notification_view.BroadcastNotificationDeleteAPI.as_view(),
         name='delete-broadcast-notification'),
    path('broadcast/delete/all/', notification_view.BroadcastNotificationDeleteAllAPI.as_view(),
         name='delete-all-broadcast-notification'),
    # Broadcast — admin CRUD
    path('broadcast/list/all/', notification_view.BroadcastNotificationListAPI.as_view(),
         name='list-all-broadcast-notifications'),
    path('broadcast/create/', notification_view.BroadcastNotificationCreateAPI.as_view(),
         name='create-broadcast-notification'),
    path('broadcast/update/id/<str:broadcast_id>/', notification_view.BroadcastNotificationUpdateAPI.as_view(),
         name='update-broadcast-notification'),
]
