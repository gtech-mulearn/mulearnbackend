"""
Admin Events API views.
All endpoints require the 'Admins' role.
"""
from django.db.models import Case, When, Value, CharField
from rest_framework.views import APIView

from db.events import Event, EventLog
from db.user import User
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.utils import CommonUtils
from utils.types import RoleType
from api.notification.service import NotificationService
from api.notification.types import NotificationType
from api.notification.audience import Audience

from .serializers import EventListItemSerializer, EventDetailSerializer, get_live_events
from .event_logger import log_event_action
from .publish_policy import resolve_terminal_status, should_announce
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


def _notify_next_approver(event, actor_id):
    """
    Notify whoever needs to act next, based on event.status right after a
    transition landed it in one of the three "awaiting review" states.
    Shared by every call site that can produce one of those transitions
    (admin/campus/mentor/company approve, and the skip-review publish path).

    The audience for each branch mirrors the authorization check the
    matching approve endpoint already uses for that exact status/organiser
    combination — this only resolves who to *notify*, it doesn't change who
    is *authorized* to approve.

    occurrence is timestamp-based (not a static "1") because an event can
    re-enter the same pending status more than once in its lifetime (e.g.
    rejected → resubmitted → pending again).

    No-op for any other status (published/rejected/completed/ongoing).
    """
    status = event.status
    if status not in (
        Event.Status.PENDING_APPROVAL,
        Event.Status.PENDING_CAMPUS_APPROVAL,
        Event.Status.PENDING_MENTOR_APPROVAL,
    ):
        return

    organiser = User.objects.filter(id=event.created_by_id).first()
    context = {
        "event_title": event.title,
        "organiser_name": organiser.full_name if organiser else "Someone",
    }
    occurrence = f"{event.id}:{event.updated_at.isoformat()}"
    kwargs = dict(
        context    = context,
        entity_id  = str(event.id),
        occurrence = occurrence,
        actor_id   = actor_id,
    )

    if status == Event.Status.PENDING_APPROVAL:
        NotificationService.dispatch(
            notif_type = NotificationType.ADMIN_EVENT_PENDING,
            audience   = Audience.admins(),
            **kwargs,
        )
        return

    if status == Event.Status.PENDING_CAMPUS_APPROVAL:
        # Same role set CampusEventApproveAPI itself gates on, scoped to
        # this event's own campus.
        from db.organization import UserOrganizationLink
        lead_ids = set(
            str(uid) for uid in
            UserOrganizationLink.objects.filter(
                org_id=event.scope_org_id, verified=True,
                user__user_role_link_user__role__title__in=[
                    RoleType.CAMPUS_LEAD.value,
                    RoleType.ZONAL_CAMPUS_LEAD.value,
                    RoleType.DISTRICT_CAMPUS_LEAD.value,
                    RoleType.ENABLER.value,
                    RoleType.LEAD_ENABLER.value,
                ],
            ).values_list('user_id', flat=True)
        )
        NotificationService.dispatch(
            notif_type = NotificationType.CAMPUS_EVENT_PENDING,
            audience   = Audience.users(list(lead_ids)),
            **kwargs,
        )
        return

    # PENDING_MENTOR_APPROVAL — the approver differs by organiser_type,
    # same as MentorEventApproveAPI/CompanyEventApproveAPI's own checks.
    if event.organiser_type == Event.OrganiserType.COMPANY:
        from db.company import Company, CompanyAdminLink
        company = Company.objects.filter(org_id=event.organiser_org_id, status='verified').first()
        if not company:
            return
        recipient_ids = {str(company.company_user_id)} | set(
            str(uid) for uid in
            CompanyAdminLink.objects.filter(
                company=company, status=CompanyAdminLink.Status.ACCEPTED,
            ).values_list('user_id', flat=True)
        )
    elif event.organiser_type == Event.OrganiserType.CAMPUS_IG:
        from db.user import MentorScopeGrant, MentorApplication
        recipient_ids = set(
            str(uid) for uid in
            MentorScopeGrant.objects.filter(
                scope_type=MentorScopeGrant.ScopeType.CAMPUS_MENTOR,
                scope_id=str(event.scope_org_id),
                is_active=True,
                application__status=MentorApplication.Status.APPROVED,
            ).values_list('application__user_id', flat=True)
        )
    elif event.organiser_type == Event.OrganiserType.GLOBAL_IG:
        from db.task import UserIgLink
        recipient_ids = set(
            str(uid) for uid in
            UserIgLink.objects.filter(
                ig_id=event.organiser_ig_id,
                assignment_type=UserIgLink.AssignmentType.MENTOR,
                is_active=True,
            ).values_list('user_id', flat=True)
        )
    else:
        recipient_ids = set()

    NotificationService.dispatch(
        notif_type = NotificationType.MENTOR_EVENT_PENDING,
        audience   = Audience.users(list(recipient_ids)),
        **kwargs,
    )


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

        # Past-dated pending events are deliberately NOT hidden: approving one
        # now resolves it to completed/ongoing rather than publishing something
        # that already happened, so an approver has to be able to see it. The
        # old exclusion left those events permanently unreachable.

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

        # Map admin events to 'mulearn' so ?search=mulearn finds them.
        events = events.annotate(
            organiser_display_name=Case(
                When(organiser_type=Event.OrganiserType.ADMIN, then=Value('mulearn')),
                default=Value(''),
                output_field=CharField(),
            )
        )

        paginated = CommonUtils.get_paginated_queryset(
            events, request,
            search_fields=[
                'title',
                'description',
                'venue_city',
                'organiser_org__title',
                'organiser_ig__name',
                'organiser_display_name',
            ],
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
        # Campus events have no admin stage at any scope — campus-level
        # approval publishes them directly.
        if (
            old_status == Event.Status.PENDING_CAMPUS_APPROVAL
            and event.organiser_type == Event.OrganiserType.CAMPUS
        ):
            new_status = Event.Status.PUBLISHED
        # Settle against the clock so an event whose date passed during review
        # is recorded as completed rather than published into the past.
        new_status = resolve_terminal_status(event, new_status)
        event.status = new_status
        event.updated_by_id = user_id
        event.save()

        log_event_action(
            event=event,
            user_id=user_id,
            action=EventLog.Action.APPROVED,
            changes={'Status': {'from': old_status, 'to': new_status}},
        )

        # Notify the event creator + fan out to scope audience
        if event.created_by_id:
            if new_status == Event.Status.PUBLISHED:
                # Fan out EVENT_PUBLISHED to all users in the event's scope
                # (campus members, IG members, company members, or all users).
                # The actor (admin approver) is auto-excluded by dispatch().
                # occurrence is timestamp-based, not just event.id: a rejected
                # event can be resubmitted and published again, and a static
                # occurrence would make the second publish notification
                # silently collide with the first under the dedupe key.
                NotificationService.dispatch(
                    notif_type = NotificationType.EVENT_PUBLISHED,
                    audience   = Audience.event_scope(str(event.id)),
                    context    = {"event_title": event.title},
                    entity_id  = str(event.id),
                    occurrence = f"{event.id}:{event.updated_at.isoformat()}",
                    actor_id   = user_id,
                )
            else:
                NotificationService.dispatch(
                    notif_type = NotificationType.EVENT_APPROVAL_STAGE,
                    audience   = Audience.user(str(event.created_by_id)),
                    context    = {"event_title": event.title, "approver_role": "admin"},
                    entity_id  = str(event.id),
                    occurrence = f"{event.id}:{event.updated_at.isoformat()}",
                    actor_id   = user_id,
                )

        # Outside the created_by_id gate above (unlike the creator notify):
        # the next approver needs to know an event is in their queue
        # regardless of whether the creator is resolvable.
        _notify_next_approver(event, user_id)

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
        if event.created_by_id:
            NotificationService.dispatch(
                notif_type = NotificationType.EVENT_REJECTED,
                audience   = Audience.user(str(event.created_by_id)),
                context    = {"event_title": event.title, "approver_role": "admin", "reason": reason},
                entity_id  = str(event.id),
                occurrence = f"{event.id}:{event.updated_at.isoformat()}",
                actor_id   = user_id,
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
