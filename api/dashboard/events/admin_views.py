"""
Admin Events API views.
All endpoints require the 'Admins' role.
"""
from rest_framework.views import APIView

from db.events import Event, EventLog
from db.user import User
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.utils import CommonUtils
from utils.types import RoleType
from api.notification.notifications_utils import NotificationUtils
from api.notification.broadcast_utils import BroadcastUtils

from .serializers import EventListItemSerializer, EventDetailSerializer, get_live_events
from .event_logger import log_event_action
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiResponse
from rest_framework import serializers as s


PENDING_STATUSES = [
    Event.Status.PENDING_CAMPUS_APPROVAL,
    Event.Status.PENDING_APPROVAL,
    Event.Status.PENDING_MENTOR_APPROVAL,
]

# Maps current status → approved status
APPROVAL_TRANSITIONS = {
    Event.Status.PENDING_CAMPUS_APPROVAL: Event.Status.PENDING_APPROVAL,
    Event.Status.PENDING_APPROVAL: Event.Status.PUBLISHED,
    Event.Status.PENDING_MENTOR_APPROVAL: Event.Status.PUBLISHED,
}


class AdminEventListAPI(APIView):
    """
    GET /events/admin/
    Returns ALL events on the platform (all statuses, including cancelled).
    Supports additional admin filters: organiser_type, created_by.
    """
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve Admin Event List.",
        responses={200: EventListItemSerializer},
    )
    def get(self, request):
        events = Event.objects.all().select_related('category', 'organiser_ig', 'organiser_org')

        params = request.query_params
        if status := params.get('status'):
            events = events.filter(status=status)
        if organiser_type := params.get('organiser_type'):
            events = events.filter(organiser_type=organiser_type)
        if created_by := params.get('created_by'):
            events = events.filter(created_by_id=created_by)
        if scope := params.get('scope'):
            events = events.filter(scope=scope)
        if is_featured := params.get('is_featured'):
            events = events.filter(is_featured=is_featured.lower() == 'true')

        paginated = CommonUtils.get_paginated_queryset(
            events, request,
            search_fields=['title', 'description', 'venue_city'],
            sort_fields={
                'created_at': 'created_at',
                'start_datetime': 'start_datetime',
                'interest_count': '-interest_count',
            },
        )
        serializer = EventListItemSerializer(
            paginated['queryset'], many=True,
            context={
                'user_id': JWTUtils.fetch_user_id(request),
                'request': request,
            },
        )
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )


class AdminEventApproveAPI(APIView):
    """
    POST /events/admin/<event_id>/approve/
    Advances a pending event through the approval pipeline.

    Transitions:
      pending_campus_approval  → pending_approval
      pending_approval         → published
      pending_mentor_approval  → published
    """
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(tags=['Dashboard - Events'], description="Create Admin Event Approve.",
        responses={200: inline_serializer(
            name='EventApproveResponse',
            fields={
                'id': s.CharField(),
                'status': s.CharField(),
            },
        )},
    )
    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)

        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()

        if event.status not in APPROVAL_TRANSITIONS:
            return CustomResponse(
                general_message=f'Event is not in a pending state (current: {event.status}).'
            ).get_failure_response()

        old_status = event.status
        new_status = APPROVAL_TRANSITIONS[event.status]
        event.status = new_status
        event.updated_by_id = user_id
        event.save()

        log_event_action(
            event=event,
            user_id=user_id,
            action=EventLog.Action.APPROVED,
            changes={'Status': {'from': old_status, 'to': new_status}},
        )

        # Notify the event creator
        actor = User.objects.filter(id=user_id).first()
        creator = event.created_by
        if creator and actor:
            if new_status == Event.Status.PUBLISHED:
                NotificationUtils.insert_notification(
                    user=creator,
                    title='Event Published',
                    description=f'Your event "{event.title}" is now live!',
                    button='View',
                    url=f'/events/{event.id}/',
                    created_by=actor,
                )
            else:
                NotificationUtils.insert_notification(
                    user=creator,
                    title='Event Approved',
                    description=f'Your event "{event.title}" has been approved and is progressing through review.',
                    button=None,
                    url=None,
                    created_by=actor,
                )

        # Fire audience broadcast when the event reaches PUBLISHED
        if new_status == Event.Status.PUBLISHED and actor:
            if event.organiser_type == Event.OrganiserType.CAMPUS_IG:
                BroadcastUtils.create_broadcast(
                    title='New Event Published',
                    description=f'A new Campus IG event "{event.title}" is now live!',
                    target_type='campus_ig',
                    target_id=event.organiser_ci_id or event.scope_ci_id,
                    created_by=actor,
                    expiry_key='event_published',
                    url=f'/events/{event.id}/',
                )
            elif event.organiser_type == Event.OrganiserType.GLOBAL_IG:
                BroadcastUtils.create_broadcast(
                    title='New Event Published',
                    description=f'A new Interest Group event "{event.title}" is now live!',
                    target_type='interest_group',
                    target_id=event.organiser_ig_id,
                    created_by=actor,
                    expiry_key='event_published',
                    url=f'/events/{event.id}/',
                )
            elif event.organiser_type == Event.OrganiserType.CAMPUS:
                BroadcastUtils.create_broadcast(
                    title='New Event Published',
                    description=f'A new Campus event "{event.title}" is now live!',
                    target_type='campus',
                    target_id=event.scope_org_id,
                    created_by=actor,
                    expiry_key='event_published',
                    url=f'/events/{event.id}/',
                )
            else:
                # ADMIN / COMPANY → global broadcast
                BroadcastUtils.create_broadcast(
                    title='New Event Published',
                    description=f'A new event "{event.title}" is now available!',
                    target_type='global',
                    target_id=None,
                    created_by=actor,
                    expiry_key='event_published',
                    url=f'/events/{event.id}/',
                )

        return CustomResponse(
            general_message=f'Event approved: {old_status} → {new_status}.',
            response={'id': event.id, 'status': new_status},
        ).get_success_response()


class AdminEventRejectAPI(APIView):
    """
    POST /events/admin/<event_id>/reject/
    Rejects a pending event, changing its status to 'rejected'.
    Body: { "reason": "..." }
    """
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(tags=['Dashboard - Events'], description="Create Admin Event Reject.",
        responses={200: inline_serializer(
            name='EventRejectResponse',
            fields={
                'id': s.CharField(),
                'status': s.CharField(),
                'reason': s.CharField(),
            },
        )},
    )
    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)

        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()

        if event.status not in PENDING_STATUSES:
            return CustomResponse(
                general_message=f'Event is not in a pending state (current: {event.status}).'
            ).get_failure_response()

        reason = request.data.get('reason', '').strip()
        if not reason:
            return CustomResponse(
                general_message='A rejection reason is required.'
            ).get_failure_response()

        old_status = event.status
        event.status = Event.Status.REJECTED
        event.updated_by_id = user_id
        event.save()

        log_event_action(
            event=event,
            user_id=user_id,
            action=EventLog.Action.REJECTED,
            changes={'Status': {'from': old_status, 'to': Event.Status.REJECTED}},
            details={'reason': reason},
        )

        # Notify the event creator
        actor = User.objects.filter(id=user_id).first()
        creator = event.created_by
        if creator and actor:
            NotificationUtils.insert_notification(
                user=creator,
                title='Event Rejected',
                description=f'Your event "{event.title}" was rejected. Reason: {reason}',
                button=None,
                url=None,
                created_by=actor,
            )

        return CustomResponse(
            general_message=f'Event rejected (was: {old_status}).',
            response={'id': event.id, 'status': Event.Status.REJECTED, 'reason': reason},
        ).get_success_response()


class AdminEventFeatureAPI(APIView):
    """
    PATCH /events/admin/<event_id>/feature/
    Toggles is_featured on/off.
    Optionally accepts body: { "is_featured": true/false }
    If not provided, current value is toggled.
    """
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(tags=['Dashboard - Events'], description="Partially update Admin Event Feature.",
        responses={200: inline_serializer(
            name='EventFeatureResponse',
            fields={
                'id': s.CharField(),
                'is_featured': s.BooleanField(),
            },
        )},
    )
    def patch(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)

        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()

        if 'is_featured' in request.data:
            new_value = bool(request.data['is_featured'])
        else:
            new_value = not event.is_featured  # toggle

        event.is_featured = new_value
        event.updated_by_id = user_id
        event.save()

        log_event_action(
            event=event,
            user_id=user_id,
            action=EventLog.Action.FEATURED if new_value else EventLog.Action.UNFEATURED,
            changes={'Featured': {'from': not new_value, 'to': new_value}},
        )

        action = 'featured' if new_value else 'unfeatured'
        return CustomResponse(
            general_message=f'Event has been {action}.',
            response={'id': event.id, 'is_featured': new_value},
        ).get_success_response()
