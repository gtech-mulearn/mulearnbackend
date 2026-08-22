from django.urls import path
from . import notification_view

urlpatterns = [

    # ── v2 User-facing notification endpoints ─────────────────────────────────
    path('',               notification_view.NotificationListView.as_view(),  name='notification-list'),
    path('unread-count/',  notification_view.UnreadCountView.as_view(),        name='notification-unread-count'),
    path('read-all/',      notification_view.MarkAllReadView.as_view(),        name='notification-read-all'),
    path('read/',          notification_view.MarkReadBulkView.as_view(),       name='notification-read-bulk'),
    path('<str:notification_id>/read/',    notification_view.MarkReadView.as_view(),   name='notification-mark-read'),
    path('<str:notification_id>/archive/', notification_view.ArchiveView.as_view(),    name='notification-archive'),
    path('<str:notification_id>/',         notification_view.DeleteOneView.as_view(),  name='notification-delete-one'),
    path('delete/all/',    notification_view.DeleteAllView.as_view(),          name='notification-delete-all'),

    # ── Legacy broadcast endpoints (admin) ────────────────────────────────────
    path('broadcast/delete/id/<str:broadcast_id>/',  notification_view.BroadcastNotificationDeleteAPI.as_view(),    name='delete-broadcast-notification'),
    path('broadcast/delete/all/',                    notification_view.BroadcastNotificationDeleteAllAPI.as_view(), name='delete-all-broadcast-notification'),
    path('broadcast/list/all/',                      notification_view.BroadcastNotificationListAPI.as_view(),      name='list-all-broadcast-notifications'),
    path('broadcast/create/',                        notification_view.BroadcastNotificationCreateAPI.as_view(),    name='create-broadcast-notification'),
    path('broadcast/update/id/<str:broadcast_id>/',  notification_view.BroadcastNotificationUpdateAPI.as_view(),    name='update-broadcast-notification'),

]
