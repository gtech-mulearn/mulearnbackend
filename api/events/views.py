from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from api.dashboard.events.event_logger import log_event_action
from api.dashboard.events.manage_views import _can_create_event
from api.dashboard.events.event_image_utils import (
    delete_stale_event_media,
    merge_event_write_payload,
)
from api.dashboard.events.public_views import (
    _build_scope_filter,
    _get_viewer_id,
)
from api.dashboard.events.serializers import (
    EventWriteSerializer,
    can_manage_event,
    get_live_events,
)
from db.events import Event, EventLog
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils


def _normalize_payload(payload):
    payload = dict(payload)

    event_type = payload.pop('type', None)
    campus_id = payload.pop('campus_id', None)
    ig_id = payload.pop('ig_id', None)
    date = payload.pop('date', None)
    location = payload.pop('location', None)

    if event_type:
        payload['scope'] = event_type
    if campus_id:
        payload['scope_org'] = campus_id
    if ig_id:
        payload['scope_ig'] = ig_id
    if location and not payload.get('venue_address'):
        payload['venue_address'] = location
    if date:
        payload.setdefault('start_datetime', f'{date}T00:00:00')
        payload.setdefault('end_datetime', f'{date}T23:59:59')

    return payload


def _apply_filters(request):
    user_id = _get_viewer_id(request)
    events = get_live_events().filter(_build_scope_filter(user_id))
    events = events.filter(status__in=[Event.Status.PUBLISHED, Event.Status.ONGOING])
    params = request.query_params

    if event_type := params.get('type'):
        events = events.filter(scope=event_type)
    if campus_id := (params.get('campus_id') or params.get('campus')):
        events = events.filter(scope_org_id=campus_id)
    if ig_id := (params.get('ig') or params.get('ig_id')):
        events = events.filter(scope_ig_id=ig_id)
    if title := params.get('title'):
        events = events.filter(title__icontains=title)
    if start_date := params.get('start_date'):
        events = events.filter(start_datetime__date__gte=start_date)
    if end_date := params.get('end_date'):
        events = events.filter(end_datetime__date__lte=end_date)

    return events, user_id


class UnifiedEventOutputSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='scope')
    created_by = serializers.CharField(source='created_by_id', read_only=True)
    campus_id = serializers.CharField(source='scope_org_id', allow_null=True, read_only=True)
    ig_id = serializers.CharField(source='scope_ig_id', allow_null=True, read_only=True)
    location = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'type', 'created_by', 'campus_id', 'ig_id', 'title',
            'description', 'start_datetime', 'end_datetime', 'location',
            'status', 'tags', 'created_at', 'updated_at',
        ]

    def get_location(self, obj):
        return obj.venue_address or obj.venue_city


class EventCollectionAPI(APIView):
    authentication_classes = [CustomizePermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        events, user_id = _apply_filters(request)
        paginated = CommonUtils.get_paginated_queryset(
            events,
            request,
            search_fields=['title', 'description', 'venue_city', 'venue_address'],
            sort_fields={'created_at': '-created_at', 'start_datetime': 'start_datetime'},
        )
        serializer = UnifiedEventOutputSerializer(
            paginated['queryset'], many=True, context={'user_id': user_id, 'request': request}
        )
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        if not _can_create_event(roles):
            return CustomResponse(
                general_message='You do not have permission to create events.'
            ).get_failure_response()

        payload, merge_error = merge_event_write_payload(request, partial=False, event=None)
        if merge_error:
            return CustomResponse(general_message=merge_error).get_failure_response()

        payload = _normalize_payload(payload)
        serializer = EventWriteSerializer(data=payload, context={'user_id': user_id})
        if not serializer.is_valid():
            return CustomResponse(response=serializer.errors).get_failure_response()

        event = serializer.save()
        return CustomResponse(
            general_message='Event created successfully.',
            response=UnifiedEventOutputSerializer(event).data,
        ).get_success_response()


class EventDetailAPI(APIView):
    authentication_classes = [CustomizePermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _get_event(self, request, event_id):
        event = Event.objects.filter(id=event_id).first()
        if not event:
            return None, None, 'Event not found.'

        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        is_admin = RoleType.ADMIN.value in roles
        if not is_admin and not can_manage_event(user_id, event):
            return None, None, 'You do not have permission to manage this event.'

        return event, user_id, None

    def patch(self, request, event_id):
        event, user_id, error = self._get_event(request, event_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response()

        if event.status in (Event.Status.CANCELLED, Event.Status.COMPLETED):
            return CustomResponse(
                general_message=f'Cannot edit a {event.status} event.'
            ).get_failure_response()

        old_cover = event.cover_image
        old_banner = event.banner_image

        payload, merge_error = merge_event_write_payload(request, partial=True, event=event)
        if merge_error:
            return CustomResponse(general_message=merge_error).get_failure_response()

        payload = _normalize_payload(payload)
        serializer = EventWriteSerializer(
            event,
            data=payload,
            partial=True,
            context={'user_id': user_id},
        )
        if not serializer.is_valid():
            return CustomResponse(response=serializer.errors).get_failure_response()

        serializer.save()
        delete_stale_event_media(old_cover, event.cover_image)
        delete_stale_event_media(old_banner, event.banner_image)
        return CustomResponse(
            general_message='Event updated successfully.',
            response=UnifiedEventOutputSerializer(event).data,
        ).get_success_response()

    def delete(self, request, event_id):
        event, user_id, error = self._get_event(request, event_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response()

        if event.status == Event.Status.CANCELLED:
            return CustomResponse(
                general_message='Event is already cancelled.'
            ).get_failure_response()

        old_status = event.status
        event.status = Event.Status.CANCELLED
        event.deleted_at = timezone.now()
        event.updated_by_id = user_id
        event.save()

        log_event_action(
            event=event,
            user_id=user_id,
            action=EventLog.Action.CANCELLED,
            changes={'Status': {'from': old_status, 'to': Event.Status.CANCELLED}},
        )

        return CustomResponse(
            general_message='Event has been cancelled.',
            response=UnifiedEventOutputSerializer(event).data,
        ).get_success_response()
