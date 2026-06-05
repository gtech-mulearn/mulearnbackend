from django.utils import timezone
from django.db.models import Prefetch, Q

from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from db.mentor import MentorshipSession, MentorshipSessionUserLink
from db.events import Event
from db.task import InterestGroup
from db.organization import Organization
from utils.response import CustomResponse
from utils.types import OrganizationType
from . import serializers
from api.dashboard.events.serializers import EventCalendarItemSerializer


def _parse_month(month_str):
    """
    Parse a 'YYYY-MM' string and return (start, end) datetime bounds for that
    month, or (None, None) if the string is absent / malformed.
    """
    if not month_str:
        return None, None
    try:
        import datetime
        year, month = map(int, month_str.split('-'))
        start = timezone.datetime(year, month, 1, tzinfo=timezone.utc)
        # First day of next month
        if month == 12:
            end = timezone.datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = timezone.datetime(year, month + 1, 1, tzinfo=timezone.utc)
        return start, end
    except (ValueError, AttributeError):
        return None, None


def _group_sessions(qs):
    """Split a MentorshipSession queryset into upcoming / ongoing / completed buckets."""
    now = timezone.now()
    upcoming, ongoing, completed = [], [], []
    for session in qs:
        if session.status == MentorshipSession.Status.COMPLETED:
            completed.append(session)
        elif session.starts_at > now:
            upcoming.append(session)
        else:
            ongoing.append(session)
    return upcoming, ongoing, completed


def _group_events(qs):
    """Split an Event queryset into upcoming / ongoing / completed buckets."""
    upcoming, ongoing, completed = [], [], []
    for event in qs:
        if event.status == Event.Status.COMPLETED:
            completed.append(event)
        elif event.status == Event.Status.ONGOING:
            ongoing.append(event)
        else:
            upcoming.append(event)
    return upcoming, ongoing, completed


# ---------------------------------------------------------------------------
# Session calendar helpers
# ---------------------------------------------------------------------------

SESSION_PREFETCH = Prefetch(
    'participant_links',
    queryset=MentorshipSessionUserLink.objects.select_related('user'),
)


class IGMentorSessionCalendar(APIView):
    @extend_schema(
        tags=['Calendar'],
        description=(
            "Calendar view of mentorship sessions for a specific Interest Group. "
            "Returns sessions grouped as upcoming, ongoing, and completed. "
            "Filter by month using the `month` query parameter (format: YYYY-MM)."
        ),
        parameters=[
            OpenApiParameter('month', OpenApiTypes.STR, description='Filter by month (YYYY-MM)', required=False),
            OpenApiParameter('status', OpenApiTypes.STR, description='Filter by status: SCHEDULED, COMPLETED, CANCELLED', required=False),
        ],
        responses={200: serializers.MentorshipSessionCalendarSerializer(many=True)},
    )
    def get(self, request, ig_id):
        ig = InterestGroup.objects.filter(id=ig_id).first()
        if not ig:
            return CustomResponse(general_message="Interest Group not found").get_failure_response()

        qs = MentorshipSession.objects.filter(
            session_type=MentorshipSession.SessionType.IG_SESSION,
            entity_id=ig_id,
            is_deleted=False,
        ).prefetch_related(SESSION_PREFETCH).order_by('starts_at')

        # Optional month filter
        month_str = request.query_params.get('month')
        start, end = _parse_month(month_str)
        if start and end:
            qs = qs.filter(starts_at__gte=start, starts_at__lt=end)

        # Optional status filter
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        upcoming, ongoing, completed = _group_sessions(qs)

        def serialize(sessions):
            return serializers.MentorshipSessionCalendarSerializer(sessions, many=True).data

        return CustomResponse(response={
            'upcoming': serialize(upcoming),
            'ongoing': serialize(ongoing),
            'completed': serialize(completed),
        }).get_success_response()


class CampusMentorSessionCalendar(APIView):
    @extend_schema(
        tags=['Calendar'],
        description=(
            "Calendar view of mentorship sessions for a specific campus. "
            "Returns sessions grouped as upcoming, ongoing, and completed. "
            "Filter by month using the `month` query parameter (format: YYYY-MM)."
        ),
        parameters=[
            OpenApiParameter('month', OpenApiTypes.STR, description='Filter by month (YYYY-MM)', required=False),
            OpenApiParameter('status', OpenApiTypes.STR, description='Filter by status: SCHEDULED, COMPLETED, CANCELLED', required=False),
        ],
        responses={200: serializers.MentorshipSessionCalendarSerializer(many=True)},
    )
    def get(self, request, campus_id):
        campus = Organization.objects.filter(
            id=campus_id, org_type=OrganizationType.COLLEGE.value
        ).first()
        if not campus:
            return CustomResponse(general_message="Campus not found").get_failure_response()

        qs = MentorshipSession.objects.filter(
            session_type=MentorshipSession.SessionType.CAMPUS_SESSION,
            entity_id=campus_id,
            is_deleted=False,
        ).prefetch_related(SESSION_PREFETCH).order_by('starts_at')

        month_str = request.query_params.get('month')
        start, end = _parse_month(month_str)
        if start and end:
            qs = qs.filter(starts_at__gte=start, starts_at__lt=end)

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        upcoming, ongoing, completed = _group_sessions(qs)

        def serialize(sessions):
            return serializers.MentorshipSessionCalendarSerializer(sessions, many=True).data

        return CustomResponse(response={
            'upcoming': serialize(upcoming),
            'ongoing': serialize(ongoing),
            'completed': serialize(completed),
        }).get_success_response()


# ---------------------------------------------------------------------------
# Event calendar views
# ---------------------------------------------------------------------------

EVENT_STATUSES_VISIBLE = [
    Event.Status.PUBLISHED,
    Event.Status.ONGOING,
    Event.Status.COMPLETED,
]

EVENT_PREFETCH = Prefetch(
    'scope_ig',
    to_attr='_scope_ig_cached',
)


class EventCalendar(APIView):
    @extend_schema(
        tags=['Calendar'],
        description=(
            "Global platform events calendar. Returns events grouped as upcoming, ongoing, "
            "and completed. Supports optional filtering by month (YYYY-MM) and scope."
        ),
        parameters=[
            OpenApiParameter('month', OpenApiTypes.STR, description='Filter by month (YYYY-MM)', required=False),
            OpenApiParameter('scope', OpenApiTypes.STR, description='Filter by scope: ig, campus, global, company', required=False),
            OpenApiParameter('status', OpenApiTypes.STR, description='Filter by status: ongoing, upcoming, completed', required=False),
        ],
        responses={200: EventCalendarItemSerializer(many=True)},
    )
    def get(self, request):
        qs = Event.objects.filter(
            status__in=EVENT_STATUSES_VISIBLE,
            deleted_at__isnull=True,
        ).select_related('category', 'organiser_ig', 'organiser_org').order_by('start_datetime')

        month_str = request.query_params.get('month')
        start, end = _parse_month(month_str)
        if start and end:
            qs = qs.filter(start_datetime__gte=start, start_datetime__lt=end)

        scope_filter = request.query_params.get('scope')
        if scope_filter:
            qs = qs.filter(scope=scope_filter.lower())

        status_filter = request.query_params.get('status')
        if status_filter:
            sf = status_filter.lower()
            if sf == 'upcoming':
                qs = qs.filter(status=Event.Status.PUBLISHED)
            elif sf == 'ongoing':
                qs = qs.filter(status=Event.Status.ONGOING)
            elif sf == 'completed':
                qs = qs.filter(status=Event.Status.COMPLETED)

        upcoming, ongoing, completed = _group_events(qs)

        def serialize(events):
            return EventCalendarItemSerializer(events, many=True).data

        return CustomResponse(response={
            'upcoming': serialize(upcoming),
            'ongoing': serialize(ongoing),
            'completed': serialize(completed),
        }).get_success_response()


class IGEventCalendar(APIView):
    @extend_schema(
        tags=['Calendar'],
        description=(
            "Events calendar scoped to a specific Interest Group. Returns events grouped as "
            "upcoming, ongoing, and completed. Supports optional month filtering."
        ),
        parameters=[
            OpenApiParameter('month', OpenApiTypes.STR, description='Filter by month (YYYY-MM)', required=False),
            OpenApiParameter('status', OpenApiTypes.STR, description='Filter by status: ongoing, upcoming, completed', required=False),
        ],
        responses={200: EventCalendarItemSerializer(many=True)},
    )
    def get(self, request, ig_id):
        ig = InterestGroup.objects.filter(id=ig_id).first()
        if not ig:
            return CustomResponse(general_message="Interest Group not found").get_failure_response()

        qs = Event.objects.filter(
            status__in=EVENT_STATUSES_VISIBLE,
            deleted_at__isnull=True,
        ).filter(
            Q(scope_ig=ig) | Q(organiser_ig=ig)
        ).select_related('category', 'organiser_ig', 'organiser_org').order_by('start_datetime').distinct()

        month_str = request.query_params.get('month')
        start, end = _parse_month(month_str)
        if start and end:
            qs = qs.filter(start_datetime__gte=start, start_datetime__lt=end)

        status_filter = request.query_params.get('status')
        if status_filter:
            sf = status_filter.lower()
            if sf == 'upcoming':
                qs = qs.filter(status=Event.Status.PUBLISHED)
            elif sf == 'ongoing':
                qs = qs.filter(status=Event.Status.ONGOING)
            elif sf == 'completed':
                qs = qs.filter(status=Event.Status.COMPLETED)

        upcoming, ongoing, completed = _group_events(qs)

        def serialize(events):
            return EventCalendarItemSerializer(events, many=True).data

        return CustomResponse(response={
            'upcoming': serialize(upcoming),
            'ongoing': serialize(ongoing),
            'completed': serialize(completed),
        }).get_success_response()


# ---------------------------------------------------------------------------
# Company Session Calendar
# ---------------------------------------------------------------------------

class CompanySessionCalendar(APIView):
    @extend_schema(
        tags=['Calendar'],
        description=(
            "Calendar view of mentorship sessions for a specific company org. "
            "Returns sessions grouped as upcoming, ongoing, and completed. "
            "Filter by month using the `month` query parameter (format: YYYY-MM)."
        ),
        parameters=[
            OpenApiParameter('month', OpenApiTypes.STR, description='Filter by month (YYYY-MM)', required=False),
            OpenApiParameter('status', OpenApiTypes.STR, description='Filter by status: SCHEDULED, COMPLETED, CANCELLED', required=False),
        ],
        responses={200: serializers.MentorshipSessionCalendarSerializer(many=True)},
    )
    def get(self, request, company_org_id):
        company_org = Organization.objects.filter(
            id=company_org_id, org_type=OrganizationType.COMPANY.value
        ).first()
        if not company_org:
            return CustomResponse(general_message="Company org not found").get_failure_response()

        qs = MentorshipSession.objects.filter(
            session_type=MentorshipSession.SessionType.COMPANY_SESSION,
            entity_id=company_org_id,
            is_deleted=False,
        ).prefetch_related(SESSION_PREFETCH).order_by('starts_at')

        month_str = request.query_params.get('month')
        start, end = _parse_month(month_str)
        if start and end:
            qs = qs.filter(starts_at__gte=start, starts_at__lt=end)

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        upcoming, ongoing, completed = _group_sessions(qs)

        def serialize(sessions):
            return serializers.MentorshipSessionCalendarSerializer(sessions, many=True).data

        return CustomResponse(response={
            'upcoming': serialize(upcoming),
            'ongoing': serialize(ongoing),
            'completed': serialize(completed),
        }).get_success_response()


class CampusEventCalendar(APIView):
    @extend_schema(
        tags=['Calendar'],
        description=(
            "Events calendar scoped to a specific Campus. Returns events grouped as "
            "upcoming, ongoing, and completed. Supports optional month filtering."
        ),
        parameters=[
            OpenApiParameter('month', OpenApiTypes.STR, description='Filter by month (YYYY-MM)', required=False),
            OpenApiParameter('status', OpenApiTypes.STR, description='Filter by status: ongoing, upcoming, completed', required=False),
        ],
        responses={200: EventCalendarItemSerializer(many=True)},
    )
    def get(self, request, campus_id):
        campus = Organization.objects.filter(
            id=campus_id, org_type=OrganizationType.COLLEGE.value
        ).first()
        if not campus:
            return CustomResponse(general_message="Campus not found").get_failure_response()

        qs = Event.objects.filter(
            status__in=EVENT_STATUSES_VISIBLE,
            deleted_at__isnull=True,
        ).filter(
            Q(scope_org=campus) | Q(organiser_org=campus)
        ).select_related('category', 'organiser_ig', 'organiser_org').order_by('start_datetime').distinct()

        month_str = request.query_params.get('month')
        start, end = _parse_month(month_str)
        if start and end:
            qs = qs.filter(start_datetime__gte=start, start_datetime__lt=end)

        status_filter = request.query_params.get('status')
        if status_filter:
            sf = status_filter.lower()
            if sf == 'upcoming':
                qs = qs.filter(status=Event.Status.PUBLISHED)
            elif sf == 'ongoing':
                qs = qs.filter(status=Event.Status.ONGOING)
            elif sf == 'completed':
                qs = qs.filter(status=Event.Status.COMPLETED)

        upcoming, ongoing, completed = _group_events(qs)

        def serialize(events):
            return EventCalendarItemSerializer(events, many=True).data

        return CustomResponse(response={
            'upcoming': serialize(upcoming),
            'ongoing': serialize(ongoing),
            'completed': serialize(completed),
        }).get_success_response()


class CompanyEventCalendar(APIView):
    @extend_schema(
        tags=['Calendar'],
        description=(
            "Events calendar scoped to a specific Company. Returns events grouped as "
            "upcoming, ongoing, and completed. Supports optional month filtering."
        ),
        parameters=[
            OpenApiParameter('month', OpenApiTypes.STR, description='Filter by month (YYYY-MM)', required=False),
            OpenApiParameter('status', OpenApiTypes.STR, description='Filter by status: ongoing, upcoming, completed', required=False),
        ],
        responses={200: EventCalendarItemSerializer(many=True)},
    )
    def get(self, request, company_id):
        company = Organization.objects.filter(
            id=company_id, org_type=OrganizationType.COMPANY.value
        ).first()
        if not company:
            return CustomResponse(general_message="Company not found").get_failure_response()

        qs = Event.objects.filter(
            status__in=EVENT_STATUSES_VISIBLE,
            deleted_at__isnull=True,
        ).filter(
            Q(scope_org=company) | Q(organiser_org=company)
        ).select_related('category', 'organiser_ig', 'organiser_org').order_by('start_datetime').distinct()

        month_str = request.query_params.get('month')
        start, end = _parse_month(month_str)
        if start and end:
            qs = qs.filter(start_datetime__gte=start, start_datetime__lt=end)

        status_filter = request.query_params.get('status')
        if status_filter:
            sf = status_filter.lower()
            if sf == 'upcoming':
                qs = qs.filter(status=Event.Status.PUBLISHED)
            elif sf == 'ongoing':
                qs = qs.filter(status=Event.Status.ONGOING)
            elif sf == 'completed':
                qs = qs.filter(status=Event.Status.COMPLETED)

        upcoming, ongoing, completed = _group_events(qs)

        def serialize(events):
            return EventCalendarItemSerializer(events, many=True).data

        return CustomResponse(response={
            'upcoming': serialize(upcoming),
            'ongoing': serialize(ongoing),
            'completed': serialize(completed),
        }).get_success_response()
