"""
Unified Dashboard Calendar API
──────────────────────────────
Single endpoint that returns events and mentor sessions based on the
caller's role (derived from the JWT token in the Authorization header).

Role-based rules:
  Mentor        → global + IG + campus + company events + mentor sessions
  Student       → global + IG + campus + company events
  Enabler       → global + IG + campus + company events
  Unauthenticated → global events + all IG-scoped events
"""

from datetime import datetime, timedelta

from django.db.models import Prefetch, Q
from django.utils import timezone

from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from db.events import Event
from db.mentor import MentorshipSession, MentorshipSessionUserLink
from db.task import UserIgLink
from db.organization import UserOrganizationLink
from db.user import UserMentor

from utils.permission import JWTUtils, CustomizePermission
from utils.response import CustomResponse
from utils.types import RoleType

from . import serializers as calendar_serializers
from api.dashboard.events.serializers import EventCalendarItemSerializer


# ───────────────────────────────────────────────────────────────
# Constants
# ───────────────────────────────────────────────────────────────

EVENT_STATUSES_VISIBLE = [
    Event.Status.PUBLISHED,
    Event.Status.ONGOING,
    Event.Status.COMPLETED,
]

SESSION_PREFETCH = Prefetch(
    'participant_links',
    queryset=MentorshipSessionUserLink.objects.select_related('user'),
)

MAX_DATE_RANGE_DAYS = 93


# ───────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────

def _get_viewer_id(request):
    """Safely extract user_id from JWT; returns None if unauthenticated."""
    if JWTUtils.is_logged_in(request):
        try:
            return JWTUtils.fetch_user_id(request)
        except Exception:
            pass
    return None


def _get_viewer_roles(request):
    """Safely extract roles from JWT; returns empty list if unauthenticated."""
    if JWTUtils.is_logged_in(request):
        try:
            return JWTUtils.fetch_role(request)
        except Exception:
            pass
    return []


def _detect_user_role(request, user_id):
    """
    Determine the caller's primary role for calendar purposes.
    Priority: mentor > enabler > student > None
    """
    if not user_id:
        return None

    roles = _get_viewer_roles(request)

    # Check if user is a mentor (via JWT role OR approved UserMentor record)
    if RoleType.MENTOR.value in roles:
        return 'mentor'

    # Also check for an active mentor scope grant (approved tier membership)
    from db.user import MentorScopeGrant
    if MentorScopeGrant.objects.filter(
        mentor__user_id=user_id,
        mentor__is_active=True,
        is_active=True,
    ).exists():
        return 'mentor'

    if RoleType.ENABLER.value in roles:
        return 'enabler'

    if RoleType.STUDENT.value in roles:
        return 'student'

    # Fallback: treat any authenticated user as student-level
    return 'student'


def _get_user_ig_ids(user_id):
    """Get list of IG IDs the user is linked to."""
    if not user_id:
        return []
    return list(
        UserIgLink.objects.filter(user_id=user_id)
        .values_list('ig_id', flat=True)
    )


def _get_user_org_ids(user_id):
    """Get list of Organisation IDs the user is linked to (verified)."""
    if not user_id:
        return []
    return list(
        UserOrganizationLink.objects.filter(user_id=user_id, verified=True)
        .values_list('org_id', flat=True)
    )


def _build_event_filter(user_role, user_ig_ids, user_org_ids):
    """
    Build Q filter for events based on the user's role.

    Campus events  → only visible to users in that specific campus
    IG events      → only visible to students in that specific IG
    Global events  → visible to everyone
    Company events → visible to everyone
    """
    # Global + Company events are always visible to everyone
    q = Q(scope=Event.Scope.GLOBAL) | Q(scope=Event.Scope.COMPANY)

    if user_role is None:
        # Unauthenticated: global + company + ALL IG-scoped events
        return q | Q(scope=Event.Scope.IG)

    # Authenticated users see their own IG events
    if user_ig_ids:
        q |= Q(scope=Event.Scope.IG, scope_ig_id__in=user_ig_ids)

    # Authenticated users see their own campus events
    if user_org_ids:
        q |= Q(scope=Event.Scope.CAMPUS, scope_org_id__in=user_org_ids)

    # Campus-IG scope: user in both org AND ig
    if user_org_ids and user_ig_ids:
        q |= Q(
            scope=Event.Scope.CAMPUS_IG,
            scope_org_id__in=user_org_ids,
            scope_ig_id__in=user_ig_ids,
        )

    return q


# ───────────────────────────────────────────────────────────────
# Main View
# ───────────────────────────────────────────────────────────────

class DashboardCalendarAPI(APIView):
    """
    GET /calendar/dashboard/
    Unified calendar endpoint. Returns events and sessions relevant
    to the caller based on their JWT token role.
    """

    @extend_schema(
        tags=['Calendar'],
        description=(
            "Unified dashboard calendar. Returns events and mentor sessions "
            "based on the caller's role (detected from JWT token). "
            "Supports date-range filtering via start_date and end_date."
        ),
        parameters=[
            OpenApiParameter(
                'month', OpenApiTypes.STR,
                description='Optional. Filter by month name. Mutually exclusive with start_date/end_date.',
                required=False,
            ),
            OpenApiParameter(
                'year', OpenApiTypes.INT,
                description='Optional. Used with month filter (defaults to current year).',
                required=False,
            ),
            OpenApiParameter(
                'start_date', OpenApiTypes.DATE,
                description='Start of date range (YYYY-MM-DD). Required if month is not provided.',
                required=False,
            ),
            OpenApiParameter(
                'end_date', OpenApiTypes.DATE,
                description='End of date range (YYYY-MM-DD). Required if month is not provided.',
                required=False,
            ),
            OpenApiParameter(
                'status', OpenApiTypes.STR,
                description='Optional. Filter by status: upcoming, ongoing, completed.',
                required=False,
            ),
        ],
        responses={200: EventCalendarItemSerializer(many=True)},
    )
    def get(self, request):
        # ── 0. Strict Authentication Check ───────────────────────
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header:
            try:
                JWTUtils.is_jwt_authenticated(request)
            except Exception:
                return CustomResponse(
                    general_message='Invalid or expired token.'
                ).get_failure_response(http_status_code=401)

        # ── 1. Parse & validate date range ───────────────────────
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        month_str = request.query_params.get('month')
        year_str = request.query_params.get('year')

        if month_str:
            month_str = month_str.lower().strip()
            month_map = {
                'january': 1, 'jan': 1, 'february': 2, 'feb': 2,
                'march': 3, 'mar': 3, 'april': 4, 'apr': 4,
                'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
                'august': 8, 'aug': 8, 'september': 9, 'sep': 9,
                'october': 10, 'oct': 10, 'november': 11, 'nov': 11,
                'december': 12, 'dec': 12
            }
            if month_str not in month_map:
                return CustomResponse(
                    general_message='Invalid month provided.'
                ).get_failure_response()
            
            month_int = month_map[month_str]
            year_int = int(year_str) if year_str and year_str.isdigit() else timezone.now().year
            
            try:
                start_dt = datetime(year_int, month_int, 1)
                if month_int == 12:
                    end_dt = datetime(year_int + 1, 1, 1)
                else:
                    end_dt = datetime(year_int, month_int + 1, 1)
                start_dt = timezone.make_aware(start_dt, timezone.utc)
                end_dt = timezone.make_aware(end_dt, timezone.utc)
            except ValueError:
                return CustomResponse(
                    general_message='Invalid year provided.'
                ).get_failure_response()

        elif start_date_str and end_date_str:
            try:
                start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
                # Make end_date inclusive
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

            if (end_dt - start_dt).days > MAX_DATE_RANGE_DAYS:
                return CustomResponse(
                    general_message=f'Date range must not exceed {MAX_DATE_RANGE_DAYS} days.'
                ).get_failure_response()
        else:
            return CustomResponse(
                general_message='Please provide either (month) OR (start_date and end_date).'
            ).get_failure_response()

        # ── 2. Detect caller context ─────────────────────────────
        user_id = _get_viewer_id(request)
        user_role = _detect_user_role(request, user_id)
        user_ig_ids = _get_user_ig_ids(user_id)
        user_org_ids = _get_user_org_ids(user_id)

        # ── 3. Build events queryset ─────────────────────────────
        event_scope_filter = _build_event_filter(user_role, user_ig_ids, user_org_ids)

        events_base_qs = (
            Event.objects.filter(
                status__in=EVENT_STATUSES_VISIBLE,
                deleted_at__isnull=True,
            )
            .filter(event_scope_filter)
            .filter(
                start_datetime__lt=end_dt,
                end_datetime__gt=start_dt,
            )
            .select_related('category', 'organiser_ig', 'organiser_org')
            .order_by('start_datetime')
            .distinct()
        )

        upcoming_events, ongoing_events, completed_events = [], [], []

        # Optional status filter for events
        status_filter = request.query_params.get('status')
        sf = status_filter.lower() if status_filter else None

        if not sf or sf == 'upcoming':
            upcoming_events = list(events_base_qs.filter(status=Event.Status.PUBLISHED)[:100])
        if not sf or sf == 'ongoing':
            ongoing_events = list(events_base_qs.filter(status=Event.Status.ONGOING)[:100])
        if not sf or sf == 'completed':
            completed_events = list(events_base_qs.filter(status=Event.Status.COMPLETED)[:100])

        # ── 4. Build sessions queryset (mentor only) ─────────────
        sessions_data = {'upcoming': [], 'ongoing': [], 'completed': []}

        if user_role == 'mentor' and user_id:
            # Get all sessions where this user is a participant (as MENTOR)
            session_ids = MentorshipSessionUserLink.objects.filter(
                user_id=user_id,
                participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
            ).values_list('session_id', flat=True)

            sessions_base_qs = (
                MentorshipSession.objects.filter(
                    id__in=session_ids,
                    is_deleted=False,
                )
                .filter(
                    starts_at__lt=end_dt,
                    ends_at__gt=start_dt,
                )
                .prefetch_related(SESSION_PREFETCH)
                .order_by('starts_at')
            )

            now = timezone.now()
            upcoming_sessions, ongoing_sessions, completed_sessions = [], [], []
            
            sf_session = status_filter.lower() if status_filter else None

            if not sf_session or sf_session == 'upcoming':
                upcoming_sessions = list(sessions_base_qs.filter(
                    status=MentorshipSession.Status.SCHEDULED,
                    starts_at__gt=now
                )[:100])

            if not sf_session or sf_session == 'ongoing':
                ongoing_sessions = list(sessions_base_qs.filter(
                    status=MentorshipSession.Status.SCHEDULED,
                    starts_at__lte=now
                )[:100])

            if not sf_session or sf_session == 'completed':
                completed_sessions = list(sessions_base_qs.filter(
                    status__in=[
                        MentorshipSession.Status.COMPLETED,
                        MentorshipSession.Status.CANCELLED,
                        MentorshipSession.Status.REJECTED
                    ]
                )[:100])

            sessions_data = {
                'upcoming': calendar_serializers.MentorshipSessionCalendarSerializer(
                    upcoming_sessions, many=True
                ).data,
                'ongoing': calendar_serializers.MentorshipSessionCalendarSerializer(
                    ongoing_sessions, many=True
                ).data,
                'completed': calendar_serializers.MentorshipSessionCalendarSerializer(
                    completed_sessions, many=True
                ).data,
            }

        # ── 5. Return combined response ──────────────────────────
        return CustomResponse(response={
            'events': {
                'upcoming': EventCalendarItemSerializer(upcoming_events, many=True).data,
                'ongoing': EventCalendarItemSerializer(ongoing_events, many=True).data,
                'completed': EventCalendarItemSerializer(completed_events, many=True).data,
            },
            'sessions': sessions_data,
        }).get_success_response()
