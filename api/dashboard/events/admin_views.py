"""
Admin Events API views.
All endpoints require the 'Admins' role.
"""
import uuid

from rest_framework.views import APIView

from db.events import Event, EventLog
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.utils import CommonUtils
from utils.types import RoleType

from .serializers import EventListItemSerializer, EventDetailSerializer, get_live_events


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
    def get(self, request):
        events = get_live_events()

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
            context={'user_id': JWTUtils.fetch_user_id(request)},
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

        EventLog.objects.create(
            id=str(uuid.uuid4()),
            event=event,
            edited_by_id=user_id,
            changed_fields=['status'],
        )

        return CustomResponse(
            general_message=f'Event approved: {old_status} → {new_status}.',
            response={'id': event.id, 'status': new_status},
        ).get_success_response()


class AdminEventRejectAPI(APIView):
    """
    POST /events/admin/<event_id>/reject/
    Rejects a pending event, returning it to 'draft'.
    Body: { "reason": "..." }
    """
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
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
        event.status = Event.Status.DRAFT
        event.updated_by_id = user_id
        event.save()

        EventLog.objects.create(
            id=str(uuid.uuid4()),
            event=event,
            edited_by_id=user_id,
            changed_fields=['status', '_rejection_reason'],
        )

        return CustomResponse(
            general_message=f'Event rejected and returned to draft (was: {old_status}).',
            response={'id': event.id, 'status': Event.Status.DRAFT, 'reason': reason},
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

        EventLog.objects.create(
            id=str(uuid.uuid4()),
            event=event,
            edited_by_id=user_id,
            changed_fields=['is_featured'],
        )

        action = 'featured' if new_value else 'unfeatured'
        return CustomResponse(
            general_message=f'Event has been {action}.',
            response={'id': event.id, 'is_featured': new_value},
        ).get_success_response()
