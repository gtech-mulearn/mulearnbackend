import uuid
from rest_framework.views import APIView
from django.db.models import Q

from db.task import Events, EventConnection
from db.user import User
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils, DateTimeUtils
from utils.types import RoleType
from .event_connection_serializer import (
    EventConnectionSerializer,
    EventConnectionCreateSerializer,
    EventConnectionStatusSerializer,
    UserEventSerializer,
    EventUserSerializer
)


# Helper Functions

def can_manage_event(user_id, event, request):
    """Check if user can manage the event (admin or event creator)"""
    try:
        roles = JWTUtils.fetch_role(request)
        if RoleType.ADMIN.value in roles:
            return True
    except:
        pass
    
    if event.created_by_id == user_id:
        return True
    
    return False


def check_user_limit(event):
    """Check if event has available slots"""
    if event.user_limit == 0:
        return True  # Unlimited
    
    # Calculate active count dynamically
    # Active = ticket_status='active' (removed/rejected/withdrawn are inactive)
    active_count = EventConnection.objects.filter(
        event=event,
        entity_type='user',
        ticket_status='active'
    ).count()
    
    return active_count < event.user_limit


def check_registration_window(event):
    """Check if registration is open for the event"""
    if not event.registration_start_date or not event.registration_end_date:
        return True  # No window restriction
    
    now = DateTimeUtils.get_current_utc_time()
    return event.registration_start_date <= now <= event.registration_end_date


# API Views

class EventJoinAPI(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        event = Events.objects.filter(id=event_id).first()
        if not event:
            return CustomResponse(
                general_message="Invalid Event id"
            ).get_failure_response()
        
        # Check registration window
        if not check_registration_window(event):
            return CustomResponse(
                general_message="Registration is not open for this event"
            ).get_failure_response()
        
        # Check user limit
        if not check_user_limit(event):
            return CustomResponse(
                general_message="Event has reached its user limit"
            ).get_failure_response()
        
        # Check if user already has an active connection
        existing_connection = EventConnection.objects.filter(
            event=event,
            entity_id=user_id,
            entity_type='user',
            ticket_status__in=['pending', 'active']
        ).first()
        
        if existing_connection:
            return CustomResponse(
                general_message="You already have a pending or active connection to this event"
            ).get_failure_response()
        
        # Create connection
        serializer = EventConnectionCreateSerializer(
            data={
                'entity_id': user_id,
                'entity_type': 'user',
                'ticket_status': 'pending'
            },
            context={
                'user_id': user_id,
                'event_id': event_id
            }
        )
        
        if serializer.is_valid():
            connection = serializer.save()
            return CustomResponse(
                general_message="Request to join event submitted successfully",
                response=EventConnectionStatusSerializer(connection).data
            ).get_success_response()
        
        return CustomResponse(
            general_message=serializer.errors
        ).get_failure_response()


class EventLeaveAPI(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        event = Events.objects.filter(id=event_id).first()
        if not event:
            return CustomResponse(
                general_message="Invalid Event id"
            ).get_failure_response()
        
        # Find active connection
        connection = EventConnection.objects.filter(
            event=event,
            entity_id=user_id,
            entity_type='user',
            ticket_status='active'
        ).first()
        
        if not connection:
            return CustomResponse(
                general_message="You are not currently joined to this event"
            ).get_failure_response()
        
        # Mark as withdrawn (user left the event voluntarily)
        connection.ticket_status = 'withdrawn'
        connection.updated_by_id = user_id
        connection.save()
        
        return CustomResponse(
            general_message="Successfully left the event"
        ).get_success_response()


class EventConnectionStatusAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        event = Events.objects.filter(id=event_id).first()
        if not event:
            return CustomResponse(
                general_message="Invalid Event id"
            ).get_failure_response()
        
        connection = EventConnection.objects.filter(
            event=event,
            entity_id=user_id,
            entity_type='user'
        ).first()
        
        if not connection:
            return CustomResponse(
                general_message="No connection found",
                response=None
            ).get_success_response()
        
        serializer = EventConnectionStatusSerializer(connection)
        return CustomResponse(
            general_message="Connection status retrieved successfully",
            response=serializer.data
        ).get_success_response()


class EventConnectionListAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        event = Events.objects.filter(id=event_id).first()
        if not event:
            return CustomResponse(
                general_message="Invalid Event id"
            ).get_failure_response()
        
        # Check permissions
        if not can_manage_event(user_id, event, request):
            return CustomResponse(
                general_message="You do not have permission to view connections for this event"
            ).get_failure_response()
        
        # Get query params
        status = request.query_params.get('status')
        entity_type = request.query_params.get('entity_type')
        
        # Build queryset
        connections = EventConnection.objects.filter(event=event)
        
        if status:
            connections = connections.filter(ticket_status=status)
        
        if entity_type:
            connections = connections.filter(entity_type=entity_type)
        
        # Paginate
        paginated_queryset = CommonUtils.get_paginated_queryset(
            connections,
            request,
            ['entity_id', 'ticket_status']
        )
        
        serializer = EventConnectionSerializer(
            paginated_queryset.get("queryset"),
            many=True
        )
        
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get("pagination")
        )


class EventConnectionApproveAPI(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request, event_id, connection_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        event = Events.objects.filter(id=event_id).first()
        if not event:
            return CustomResponse(
                general_message="Invalid Event id"
            ).get_failure_response()
        
        # Check permissions
        if not can_manage_event(user_id, event, request):
            return CustomResponse(
                general_message="You do not have permission to manage this event"
            ).get_failure_response()
        
        connection = EventConnection.objects.filter(
            id=connection_id,
            event=event
        ).first()
        
        if not connection:
            return CustomResponse(
                general_message="Invalid connection id"
            ).get_failure_response()
        
        if connection.ticket_status != 'pending':
            return CustomResponse(
                general_message="Only pending requests can be approved"
            ).get_failure_response()
        
        # Check user limit before approving
        if not check_user_limit(event):
            return CustomResponse(
                general_message="Event has reached its user limit"
            ).get_failure_response()
        
        # Approve
        connection.ticket_status = 'active'
        connection.updated_by_id = user_id
        connection.save()
        
        return CustomResponse(
            general_message="Request approved successfully",
            response=EventConnectionSerializer(connection).data
        ).get_success_response()


class EventConnectionRejectAPI(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request, event_id, connection_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        event = Events.objects.filter(id=event_id).first()
        if not event:
            return CustomResponse(
                general_message="Invalid Event id"
            ).get_failure_response()
        
        # Check permissions
        if not can_manage_event(user_id, event, request):
            return CustomResponse(
                general_message="You do not have permission to manage this event"
            ).get_failure_response()
        
        connection = EventConnection.objects.filter(
            id=connection_id,
            event=event
        ).first()
        
        if not connection:
            return CustomResponse(
                general_message="Invalid connection id"
            ).get_failure_response()
        
        if connection.ticket_status not in ['pending', 'active']:
            return CustomResponse(
                general_message="This connection cannot be rejected"
            ).get_failure_response()
        
        # Reject (only if pending, otherwise remove)
        # If pending -> rejected, if active -> removed (admin action)
        if connection.ticket_status == 'pending':
            connection.ticket_status = 'rejected'
        else:
            connection.ticket_status = 'removed'  # Admin removes active connection
        
        connection.updated_by_id = user_id
        connection.save()
        
        return CustomResponse(
            general_message="Request rejected successfully",
            response=EventConnectionSerializer(connection).data
        ).get_success_response()


class EventConnectionAddUserAPI(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        event = Events.objects.filter(id=event_id).first()
        if not event:
            return CustomResponse(
                general_message="Invalid Event id"
            ).get_failure_response()
        
        # Check permissions
        if not can_manage_event(user_id, event, request):
            return CustomResponse(
                general_message="You do not have permission to manage this event"
            ).get_failure_response()
        
        target_user_id = request.data.get('user_id')
        if not target_user_id:
            return CustomResponse(
                general_message="user_id is required"
            ).get_failure_response()
        
        # Check if user exists
        target_user = User.objects.filter(id=target_user_id).first()
        if not target_user:
            return CustomResponse(
                general_message="Invalid user id"
            ).get_failure_response()
        
        # Check user limit
        if not check_user_limit(event):
            return CustomResponse(
                general_message="Event has reached its user limit"
            ).get_failure_response()
        
        # Check if user already has active connection
        existing_connection = EventConnection.objects.filter(
            event=event,
            entity_id=target_user_id,
            entity_type='user',
            ticket_status__in=['pending', 'active']
        ).first()
        
        if existing_connection:
            return CustomResponse(
                general_message="User already has an active connection to this event"
            ).get_failure_response()
        
        # Create connection with active status
        serializer = EventConnectionCreateSerializer(
            data={
                'entity_id': target_user_id,
                'entity_type': 'user',
                'ticket_status': 'active'
            },
            context={
                'user_id': user_id,
                'event_id': event_id
            }
        )
        
        if serializer.is_valid():
            connection = serializer.save()
            
            return CustomResponse(
                general_message="User added to event successfully",
                response=EventConnectionSerializer(connection).data
            ).get_success_response()
        
        return CustomResponse(
            general_message=serializer.errors
        ).get_failure_response()


class EventConnectionRemoveUserAPI(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request, event_id, connection_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        event = Events.objects.filter(id=event_id).first()
        if not event:
            return CustomResponse(
                general_message="Invalid Event id"
            ).get_failure_response()
        
        # Check permissions
        if not can_manage_event(user_id, event, request):
            return CustomResponse(
                general_message="You do not have permission to manage this event"
            ).get_failure_response()
        
        connection = EventConnection.objects.filter(
            id=connection_id,
            event=event
        ).first()
        
        if not connection:
            return CustomResponse(
                general_message="Invalid connection id"
            ).get_failure_response()
        
        if connection.ticket_status != 'active':
            return CustomResponse(
                general_message="Connection is not active"
            ).get_failure_response()
        
        # Mark as removed (admin removed user from event)
        connection.ticket_status = 'removed'
        connection.updated_by_id = user_id
        connection.save()
        
        return CustomResponse(
            general_message="User removed from event successfully",
            response=EventConnectionSerializer(connection).data
        ).get_success_response()


class EventUsersByStatusAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request, event_id, ticket_status):
        user_id = JWTUtils.fetch_user_id(request)
        
        event = Events.objects.filter(id=event_id).first()
        if not event:
            return CustomResponse(
                general_message="Invalid Event id"
            ).get_failure_response()
        
        # Check permissions - only event creator and admin can access
        if not can_manage_event(user_id, event, request):
            return CustomResponse(
                general_message="You do not have permission to view users for this event"
            ).get_failure_response()
        
        # Validate ticket_status
        valid_statuses = ['pending', 'active', 'removed', 'rejected', 'withdrawn']
        if ticket_status not in valid_statuses:
            return CustomResponse(
                general_message=f"Invalid ticket status. Valid statuses are: {', '.join(valid_statuses)}"
            ).get_failure_response()
        
        # Filter connections by event, ticket_status, and entity_type='user'
        connections = EventConnection.objects.filter(
            event=event,
            ticket_status=ticket_status,
            entity_type='user'
        )
        
        # Paginate
        paginated_queryset = CommonUtils.get_paginated_queryset(
            connections,
            request,
            ['entity_id', 'ticket_status', 'created_at']
        )
        
        serializer = EventConnectionSerializer(
            paginated_queryset.get("queryset"),
            many=True
        )
        
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get("pagination")
        )


class UserEventsAPI(APIView):
    """API for users to view their own events"""
    authentication_classes = [CustomizePermission]

    def get(self, request, ticket_status=None):
        user_id = JWTUtils.fetch_user_id(request)
        
        # Validate ticket_status if provided
        if ticket_status:
            valid_statuses = ['pending', 'active', 'removed', 'rejected', 'withdrawn']
            if ticket_status not in valid_statuses:
                return CustomResponse(
                    general_message=f"Invalid ticket status. Valid statuses are: {', '.join(valid_statuses)}"
                ).get_failure_response()
        
        # Build connection filter
        connection_filter = {
            'entity_id': user_id,
            'entity_type': 'user'
        }
        if ticket_status:
            connection_filter['ticket_status'] = ticket_status
        
        # Get all connections for this user
        connections = EventConnection.objects.filter(**connection_filter)
        
        # Get event IDs from connections
        event_ids = connections.values_list('event_id', flat=True).distinct()
        
        if not event_ids:
            # Return empty paginated response
            return CustomResponse().paginated_response(
                data=[],
                pagination={
                    'count': 0,
                    'totalPages': 0,
                    'isNext': False,
                    'isPrev': False,
                    'nextPage': None
                }
            )
        
        # Get events (only basic fields needed)
        events = Events.objects.filter(id__in=event_ids)
        
        # Paginate
        paginated_queryset = CommonUtils.get_paginated_queryset(
            events,
            request,
            ['name', 'event_start_date', 'created_at']
        )
        
        # Get paginated event IDs and fetch their connections
        paginated_events = paginated_queryset.get("queryset")
        paginated_event_ids = [event.id for event in paginated_events]
        
        # Fetch connections for paginated events
        user_connections = EventConnection.objects.filter(
            event_id__in=paginated_event_ids,
            entity_id=user_id,
            entity_type='user'
        )
        if ticket_status:
            user_connections = user_connections.filter(ticket_status=ticket_status)
        
        # Create connection map
        connection_map = {conn.event_id: conn for conn in user_connections}
        
        # Attach connections to events
        for event in paginated_events:
            event.connection = connection_map.get(event.id)
        
        serializer = UserEventSerializer(
            paginated_events,
            many=True
        )
        
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get("pagination")
        )


class EventUsersListAPI(APIView):
    """API to list all users in an event - only admin and event creator can access"""
    authentication_classes = [CustomizePermission]

    def get(self, request, event_id, ticket_status=None):
        user_id = JWTUtils.fetch_user_id(request)
        
        event = Events.objects.filter(id=event_id).first()
        if not event:
            return CustomResponse(
                general_message="Invalid Event id"
            ).get_failure_response()
        
        # Check permissions - only event creator and admin can access
        if not can_manage_event(user_id, event, request):
            return CustomResponse(
                general_message="You do not have permission to view users for this event"
            ).get_failure_response()
        
        # If ticket_status not in path, check query params (backward compatibility)
        if not ticket_status:
            ticket_status = request.query_params.get('ticket_status')
        
        # Filter connections by event and entity_type='user' (only users)
        connections = EventConnection.objects.filter(
            event=event,
            entity_type='user'
        )
        
        # Filter by ticket_status if provided
        if ticket_status:
            valid_statuses = ['pending', 'active', 'removed', 'rejected', 'withdrawn']
            if ticket_status not in valid_statuses:
                return CustomResponse(
                    general_message=f"Invalid ticket status. Valid statuses are: {', '.join(valid_statuses)}"
                ).get_failure_response()
            connections = connections.filter(ticket_status=ticket_status)
        
        # Paginate
        paginated_queryset = CommonUtils.get_paginated_queryset(
            connections,
            request,
            ['entity_id', 'ticket_status', 'created_at']
        )
        
        serializer = EventUserSerializer(
            paginated_queryset.get("queryset"),
            many=True
        )
        
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get("pagination")
        )
