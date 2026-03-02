"""
Public Events API views — no special role required, but some
endpoints benefit from an authenticated user context.
"""
from rest_framework.views import APIView

from db.events import Event, EventInterest
from db.task import Wallet, UserIgLink
from db.organization import UserOrganizationLink
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils, DateTimeUtils

from .serializers import (
    EventListItemSerializer,
    EventDetailSerializer,
    get_live_events,
)
import uuid


def _get_viewer_id(request):
    """Safely extract user_id; returns None if unauthenticated."""
    try:
        return JWTUtils.fetch_user_id(request)
    except Exception:
        return None


def _build_scope_filter(user_id):
    """
    Returns a list of Q-compatible kwargs to use in an OR-filter
    so we show only events accessible to this viewer.

    Visibility rules:
      - scope=global     → always visible
      - scope=campus     → user must be in scope_org
      - scope=ig         → user must be in scope_ig
      - scope=campus_ig  → user must be in scope_org AND scope_ig
      - scope=company    → user must be in organiser_org (company)
    """
    from django.db.models import Q

    # Always show global events
    q = Q(scope=Event.Scope.GLOBAL)

    if not user_id:
        return q  # Unauthenticated: global only

    # Campus scope: user's organisation matches scope_org
    user_org_ids = list(
        UserOrganizationLink.objects.filter(user_id=user_id, verified=True)
        .values_list('org_id', flat=True)
    )
    if user_org_ids:
        q |= Q(scope=Event.Scope.CAMPUS, scope_org_id__in=user_org_ids)

    # IG scope: user's IGs match scope_ig
    user_ig_ids = list(
        UserIgLink.objects.filter(user_id=user_id)
        .values_list('ig_id', flat=True)
    )
    if user_ig_ids:
        q |= Q(scope=Event.Scope.IG, scope_ig_id__in=user_ig_ids)

    # Campus-IG scope: user in org AND in ig
    if user_org_ids and user_ig_ids:
        q |= Q(scope=Event.Scope.CAMPUS_IG,
                scope_org_id__in=user_org_ids,
                scope_ig_id__in=user_ig_ids)

    # Company scope: user belongs to company that's the organiser
    if user_org_ids:
        q |= Q(scope=Event.Scope.COMPANY, organiser_org_id__in=user_org_ids)

    return q


class EventListAPI(APIView):
    """
    GET /events/
    Public paginated list of events.
    Applies scope visibility rules, then optional filters from query params.
    """
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = _get_viewer_id(request)

        # Base: live events the viewer can see
        scope_filter = _build_scope_filter(user_id)
        events = get_live_events().filter(scope_filter)

        # Default: published + ongoing only
        events = events.filter(
            status__in=[Event.Status.PUBLISHED, Event.Status.ONGOING]
        )

        # Optional query-param filters
        params = request.query_params

        if event_type := params.get('event_type'):
            events = events.filter(organiser_type=event_type)
        if ig_id := params.get('ig_id'):
            events = events.filter(scope_ig_id=ig_id)
        if campus_id := params.get('campus_id'):
            events = events.filter(scope_org_id=campus_id)
        if cluster := params.get('cluster'):
            # Filter by organiser IG's category (cluster proxy)
            events = events.filter(organiser_ig__category=cluster)
        if is_featured := params.get('is_featured'):
            events = events.filter(is_featured=is_featured.lower() == 'true')
        if start_date := params.get('start_date'):
            events = events.filter(start_datetime__date__gte=start_date)
        if end_date := params.get('end_date'):
            events = events.filter(end_datetime__date__lte=end_date)
        if tags := params.get('tags'):
            # tags is a JSON array field; search for a tag value
            events = events.filter(tags__icontains=tags)

        # Karma eligibility filter
        if params.get('eligible_only') == 'true' and user_id:
            from django.db.models import Q as DjQ
            try:
                karma = Wallet.objects.filter(user_id=user_id).values_list('karma', flat=True).first() or 0
            except Exception:
                karma = 0
            events = events.filter(
                DjQ(min_karma__isnull=True) | DjQ(min_karma__lte=karma)
            )

        sort_fields = {
            'start_datetime': 'start_datetime',
            '-start_datetime': '-start_datetime',
            'interest_count': '-interest_count',
            'created_at': 'created_at',
        }

        paginated = CommonUtils.get_paginated_queryset(
            events, request,
            search_fields=['title', 'description', 'venue_city'],
            sort_fields=sort_fields,
        )

        serializer = EventListItemSerializer(
            paginated['queryset'], many=True,
            context={'user_id': user_id, 'request': request},
        )
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )


class EventFeaturedAPI(APIView):
    """
    GET /events/featured/
    Featured published events — no auth required.
    """

    def get(self, request):
        events = get_live_events().filter(
            is_featured=True,
            status=Event.Status.PUBLISHED,
        ).order_by('start_datetime')[:20]

        serializer = EventListItemSerializer(events, many=True, context={'user_id': None})
        return CustomResponse(
            general_message='Featured events retrieved.',
            response=serializer.data,
        ).get_success_response()


class EventDetailAPI(APIView):
    """
    GET /events/<event_id>/
    Full event detail. Scope-checked; draft/pending visible only to organiser/admin.
    """
    authentication_classes = [CustomizePermission]

    def get(self, request, event_id):
        user_id = _get_viewer_id(request)

        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(
                general_message='Event not found.'
            ).get_failure_response()

        # Draft / pending events: only organiser and admins
        non_public_statuses = [
            Event.Status.DRAFT,
            Event.Status.PENDING_CAMPUS_APPROVAL,
            Event.Status.PENDING_APPROVAL,
            Event.Status.PENDING_MENTOR_APPROVAL,
        ]
        if event.status in non_public_statuses:
            if not user_id:
                return CustomResponse(
                    general_message='Event not found.'
                ).get_failure_response()
            try:
                roles = JWTUtils.fetch_role(request)
                from utils.types import RoleType
                from .serializers import can_manage_event
                is_admin = RoleType.ADMIN.value in roles
                if not is_admin and not can_manage_event(user_id, event):
                    return CustomResponse(
                        general_message='Event not found.'
                    ).get_failure_response()
            except Exception:
                return CustomResponse(
                    general_message='Event not found.'
                ).get_failure_response()

        serializer = EventDetailSerializer(
            event,
            context={'user_id': user_id, 'request': request},
        )
        return CustomResponse(
            general_message='Event detail retrieved.',
            response=serializer.data,
        ).get_success_response()


class EventInterestAPI(APIView):
    """
    POST   /events/<event_id>/interest/  → Express "I'm Going"
    DELETE /events/<event_id>/interest/  → Remove interest
    """
    authentication_classes = [CustomizePermission]

    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)

        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()

        if event.status not in (Event.Status.PUBLISHED, Event.Status.ONGOING):
            return CustomResponse(
                general_message='Cannot express interest in an unpublished event.'
            ).get_failure_response()

        # Check min_karma gate
        if event.min_karma:
            try:
                karma = Wallet.objects.filter(user_id=user_id).values_list('karma', flat=True).first() or 0
            except Exception:
                karma = 0
            if karma < event.min_karma:
                return CustomResponse(
                    general_message=f'You need {event.min_karma:,} karma to access this event.'
                ).get_failure_response()

        _, created = EventInterest.objects.get_or_create(
            event=event,
            user_id=user_id,
            defaults={'id': str(uuid.uuid4())},
        )

        if created:
            # Triggers handle interest_count. If triggers are disabled, update manually:
            Event.objects.filter(id=event_id).update(interest_count=models.F('interest_count') + 1)
            msg = "You're now marked as interested in this event."
        else:
            msg = 'You have already expressed interest in this event.'

        return CustomResponse(
            general_message=msg,
            response={'event_id': event_id, 'user_id': user_id, 'status': 'interested'},
        ).get_success_response()

    def delete(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)

        interest = EventInterest.objects.filter(event_id=event_id, user_id=user_id).first()
        if not interest:
            return CustomResponse(
                general_message='You have not expressed interest in this event.'
            ).get_failure_response()

        interest.delete()
        # Triggers handle the decrement. If triggers are disabled:
        Event.objects.filter(id=event_id).update(interest_count=models.F('interest_count') - 1)

        return CustomResponse(
            general_message='Your interest has been removed.'
        ).get_success_response()
