"""
Public Events API views — no special role required, but some
endpoints benefit from an authenticated user context.
"""
import uuid

from django.db.models import F, Q, Exists, OuterRef
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from db.events import Event, EventInterest
from db.task import Wallet, UserIgLink
from db.organization import UserOrganizationLink
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils

from datetime import datetime
from django.utils import timezone

from .serializers import (
    EventListItemSerializer,
    EventDetailSerializer,
    get_live_events,
    EventCalendarItemSerializer,
)
from drf_spectacular.utils import extend_schema
from utils.schema_utils import CustomResponseSerializer


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

    # Company scope: event is scoped to a company the user belongs to
    if user_org_ids:
        q |= Q(scope=Event.Scope.COMPANY, scope_org_id__in=user_org_ids)

    return q


def _public_events_queryset(request, *, featured_only=False):
    """
    Base queryset for public event lists: scope visibility, published/ongoing,
    optional filters. When ``featured_only`` is True, only ``is_featured`` rows
    are returned (used by /events/featured/ and /events/is-featured/).
    """
    user_id = _get_viewer_id(request)

    scope_filter = _build_scope_filter(user_id)
    events = get_live_events().select_related('category', 'organiser_ig', 'organiser_org').filter(scope_filter)

    events = events.filter(
        status__in=[Event.Status.PUBLISHED, Event.Status.ONGOING]
    )

    if featured_only:
        events = events.filter(is_featured=True)

    params = request.query_params

    if event_type := params.get('event_type'):
        events = events.filter(organiser_type=event_type)
    if ig_id := params.get('ig_id'):
        events = events.filter(scope_ig_id=ig_id)
    if campus_id := params.get('campus_id'):
        events = events.filter(scope_org_id=campus_id)
    if cluster := params.get('cluster'):
        events = events.filter(organiser_ig__category=cluster)
    if not featured_only:
        if is_featured := params.get('is_featured'):
            events = events.filter(is_featured=is_featured.lower() == 'true')
    if start_date := params.get('start_date'):
        events = events.filter(start_datetime__date__gte=start_date)
    if end_date := params.get('end_date'):
        events = events.filter(end_datetime__date__lte=end_date)
    if tags := params.get('tags'):
        events = events.filter(tags__icontains=tags)

    if params.get('eligible_only') == 'true' and user_id:
        try:
            karma = Wallet.objects.filter(user_id=user_id).values_list('karma', flat=True).first() or 0
        except Exception:
            karma = 0
        events = events.filter(
            Q(min_karma__isnull=True) | Q(min_karma__lte=karma)
        )

    if user_id:
        events = events.annotate(
            viewer_interested=Exists(
                EventInterest.objects.filter(event=OuterRef('pk'), user_id=user_id)
            )
        )

    return events, user_id


_PUBLIC_EVENT_SORT_FIELDS = {
    'start_datetime': 'start_datetime',
    '-start_datetime': '-start_datetime',
    'interest_count': '-interest_count',
    'created_at': 'created_at',
}


class EventListAPI(APIView):
    """
    GET /events/
    Public paginated list of events.
    Applies scope visibility rules, then optional filters from query params.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve Event List.",
        responses={200: EventListItemSerializer},
    )
    def get(self, request):
        events, user_id = _public_events_queryset(request, featured_only=False)

        paginated = CommonUtils.get_paginated_queryset(
            events, request,
            search_fields=['title', 'description', 'venue_city'],
            sort_fields=_PUBLIC_EVENT_SORT_FIELDS,
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
    GET /events/featured/  and  GET /events/is-featured/

    Featured events the viewer may see (same scope rules as GET /events/),
    ``is_featured=True``, status published or ongoing. Paginated; optional JWT
    for ``viewer_interest_status``.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve Event Featured.",
        responses={200: EventListItemSerializer},
    )
    def get(self, request):
        events, user_id = _public_events_queryset(request, featured_only=True)

        paginated = CommonUtils.get_paginated_queryset(
            events, request,
            search_fields=['title', 'description', 'venue_city'],
            sort_fields=_PUBLIC_EVENT_SORT_FIELDS,
        )

        serializer = EventListItemSerializer(
            paginated['queryset'], many=True,
            context={'user_id': user_id, 'request': request},
        )
        return CustomResponse(
            general_message='Featured events retrieved.',
        ).paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )


class EventDetailAPI(APIView):
    """
    GET /events/<event_id>/
    Full event detail. Scope-checked; draft/pending visible only to organiser/admin.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve Event Detail.",
        responses={200: EventDetailSerializer},
    )
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

    @extend_schema(tags=['Dashboard - Events'], description="Create Event Interest.",
        responses={200: CustomResponseSerializer},
    )
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
            Event.objects.filter(id=event_id).update(interest_count=F('interest_count') + 1)
            msg = "You're now marked as interested in this event."
        else:
            msg = 'You have already expressed interest in this event.'

        return CustomResponse(
            general_message=msg,
            response={'event_id': event_id, 'user_id': user_id, 'status': 'interested'},
        ).get_success_response()

    @extend_schema(tags=['Dashboard - Events'], description="Delete Event Interest.",
        responses={200: CustomResponseSerializer},
    )
    def delete(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)

        interest = EventInterest.objects.filter(event_id=event_id, user_id=user_id).first()
        if not interest:
            return CustomResponse(
                general_message='You have not expressed interest in this event.'
            ).get_failure_response()

        interest.delete()
        Event.objects.filter(id=event_id).update(interest_count=F('interest_count') - 1)

        return CustomResponse(
            general_message='Your interest has been removed.'
        ).get_success_response()


class EventCalendarAPI(APIView):
    """
    GET /events/calendar/
    Returns a list of events overlapping the requested date range, formatted for frontend calendar display.
    Query Params:
      - start_date (YYYY-MM-DD, mandatory)
      - end_date   (YYYY-MM-DD, mandatory)
    """

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve Event Calendar.",
        responses={200: EventCalendarItemSerializer},
    )
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date or not end_date:
            return CustomResponse(
                general_message='Both start_date and end_date query parameters are required.'
            ).get_failure_response()

        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            from datetime import timedelta
            # Add 1 day to end_dt to make it inclusive of the requested end date
            end_dt = end_dt + timedelta(days=1)
            
            start_dt = timezone.make_aware(start_dt, timezone.utc)
            end_dt = timezone.make_aware(end_dt, timezone.utc)
        except ValueError:
            return CustomResponse(
                general_message='Invalid date format. Use YYYY-MM-DD.'
            ).get_failure_response()

        if start_dt >= end_dt:
            return CustomResponse(
                general_message='start_date must be before or equal to end_date.'
            ).get_failure_response()

        if (end_dt - start_dt).days > 94:
            return CustomResponse(
                general_message='Date range must not exceed 93 days.'
            ).get_failure_response()

        user_id = _get_viewer_id(request)
        scope_filter = _build_scope_filter(user_id)
        
        events = (
            get_live_events()
            .select_related('category', 'organiser_ig', 'organiser_org')
            .filter(scope_filter)
            .filter(
                status__in=[Event.Status.PUBLISHED, Event.Status.ONGOING, Event.Status.COMPLETED],
                start_datetime__lt=end_dt,
                end_datetime__gt=start_dt,
            )
            .order_by('start_datetime', 'end_datetime')
        )

        serializer = EventCalendarItemSerializer(events, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

