from django.urls import path

from . import events_views
from . import event_connection_views

urlpatterns = [
    path('', events_views.EventAPI.as_view()),
    path('my-events/', event_connection_views.UserEventsAPI.as_view()),
    path('my-events/<str:ticket_status>/', event_connection_views.UserEventsAPI.as_view()),
    path('<str:event_id>/', events_views.EventAPI.as_view()),
    path('<str:event_id>/join/', event_connection_views.EventJoinAPI.as_view()),
    path('<str:event_id>/leave/', event_connection_views.EventLeaveAPI.as_view()),
    path('<str:event_id>/my-status/', event_connection_views.EventConnectionStatusAPI.as_view()),
    path('<str:event_id>/connections/', event_connection_views.EventConnectionListAPI.as_view()),
    path('<str:event_id>/users/<str:ticket_status>/', event_connection_views.EventUsersListAPI.as_view()),
    path('<str:event_id>/users/', event_connection_views.EventUsersListAPI.as_view()),
    path('<str:event_id>/connections/add-user/', event_connection_views.EventConnectionAddUserAPI.as_view()),
    path('<str:event_id>/connections/<str:connection_id>/approve/', event_connection_views.EventConnectionApproveAPI.as_view()),
    path('<str:event_id>/connections/<str:connection_id>/reject/', event_connection_views.EventConnectionRejectAPI.as_view()),
    path('<str:event_id>/connections/<str:connection_id>/remove/', event_connection_views.EventConnectionRemoveUserAPI.as_view()),
    path('<str:event_id>/<str:ticket_status>/', event_connection_views.EventUsersByStatusAPI.as_view()),
]
