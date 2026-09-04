"""
Manage Events API views.
Organiser / co-owner access required for all endpoints.
"""
import uuid
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from db.events import Event, EventConnection, EventLog
from db.user import User
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils
from utils.types import RoleType
from api.notification.notifications_utils import NotificationUtils
from api.notification.broadcast_utils import BroadcastUtils

from .serializers import (
    EventListItemSerializer,
    EventDetailSerializer,
    EventCoOwnerSerializer,
    EventCollaboratorSerializer,
    MyEventInviteSerializer,
    EventLogSerializer,
    EventWriteSerializer,
    can_manage_event,
    get_live_events,
)
from .event_logger import log_event_action
from .event_image_utils import delete_event_media_paths, delete_stale_event_media, merge_event_write_payload
from .publish_policy import (
    CAMPUS_AUTHORITY_ROLES,
    decide_publish_status,
    is_editable,
    resolve_terminal_status,
    should_announce,
)
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s


MANAGEABLE_ROLES = {
    RoleType.ADMIN.value,
    RoleType.CAMPUS_LEAD.value,
    RoleType.IG_LEAD.value,
    RoleType.ZONAL_CAMPUS_LEAD.value,
    RoleType.DISTRICT_CAMPUS_LEAD.value,
    RoleType.COMPANY.value,
    RoleType.ENABLER.value,
    RoleType.LEAD_ENABLER.value,
    RoleType.MENTOR.value,
}

# PRD §15 — rate/abuse limit on company event creation volume.
MAX_OPEN_COMPANY_EVENTS = 5


def _can_create_event(roles):
    """True if user holds at least one event-creation role."""
    if MANAGEABLE_ROLES.intersection(set(roles)):
        return True
    # Dynamic IG/campus roles: e.g. "WEBDEV IGLead", "WEBDEV CampusLead"
    return any(r.endswith(' IGLead') or r.endswith(' CampusLead') for r in roles)


def _get_manageable_events():
    """Base queryset for manage views: includes cancelled events but not hard-deleted rows.
    Organisers need to see their own cancelled events (soft-delete sets deleted_at)."""
    return Event.objects.all()  # No deleted_at filter — managers see everything they own


def _get_user_company_org_ids(user_id, roles):
    """
    Returns a list of Organization IDs for companies where the user is the
    owner, an accepted co-admin delegate, or a COMPANY_MENTOR. Ownership/
    co-admin membership is checked directly rather than gated on
    RoleType.COMPANY, since only the true registering owner is ever granted
    that platform role — an accepted CompanyAdminLink delegate never is.
    """
    from db.company import Company, CompanyAdminLink
    from django.db.models import Q

    company_org_ids = set()
    for company in Company.objects.filter(
        Q(company_user_id=user_id) | Q(
            admin_links__user_id=user_id,
            admin_links__status=CompanyAdminLink.Status.ACCEPTED,
        ),
        status="verified",
    ).distinct():
        if company.org_id:
            company_org_ids.add(company.org_id)

    if RoleType.MENTOR.value in roles:
        # This part remains as is, for mentors creating events for their company.
        # The check above handles owners and delegates.
        from db.user import MentorScopeGrant
        from api.dashboard.mentor.dash_mentor_helper import get_scope_ids
        company_org_ids |= get_scope_ids(user_id, MentorScopeGrant.ScopeType.COMPANY_MENTOR)

    return list(company_org_ids)


def _is_active_campus_member(user_id, org_id):
    """True if user_id has a non-alumni UserOrganizationLink to org_id.

    A graduated user keeps their UserOrganizationLink row (graduation_year
    stays on record) with is_alumni flipped to True by
    mu_celery.alumni_cron.update_alumni_status_cron — that cron only updates
    is_alumni, it does not revoke any role the user still holds. A stale
    CampusLead-type role for a graduated user must not keep counting as
    authority over that campus's events, so every campus-membership check
    goes through here rather than a bare .exists().
    """
    from django.db.models import Q
    from db.organization import UserOrganizationLink
    return UserOrganizationLink.objects.filter(
        user_id=user_id, org_id=org_id
    ).filter(Q(is_alumni=False) | Q(is_alumni__isnull=True)).exists()


def _validate_campus_event_ownership(user_id, roles, organiser_type, organiser_org_id):
    """Tenancy guard for Campus (campus-wide) events.

    Returns an error message if the caller is not a member of the campus the
    event targets, else None. Admins bypass. Prevents a lead of one campus from
    creating/publishing campus-wide events scoped to a different campus.

    Note: Campus IG events are intentionally not covered here. The current
    event schema stores only the IG (scope_ci_id / organiser_ci_id) for
    campus_ig events and does not reliably record the owning campus
    (scope_org is null from the create wizard), so campus-level ownership
    cannot be enforced for them yet.
    """
    if RoleType.ADMIN.value in roles:
        return None

    if organiser_type != Event.OrganiserType.CAMPUS.value:
        return None

    if not organiser_org_id:
        return 'A target campus is required for campus events.'

    if not _is_active_campus_member(user_id, organiser_org_id):
        return 'You are not authorized to create events for this campus.'
    return None


def _resolve_publish_authority(user_id, roles, event):
    """Resolve the caller's standing to publish/republish `event` right now.

    Shared by the publish endpoint and the reschedule-revival path in
    ManageEventDetailAPI._update, so authority is always evaluated fresh
    against the event's own organiser/campus rather than assumed to still
    hold from whenever it was last approved.
    """
    is_campus_authority = False
    is_campus_mentor = False
    is_ig_mentor_assigned = False
    is_company_owner = False

    if event.organiser_type == Event.OrganiserType.CAMPUS:
        is_campus_authority = bool(
            CAMPUS_AUTHORITY_ROLES.intersection(roles)
        ) and _is_active_campus_member(user_id, event.organiser_org_id)
    elif event.organiser_type == Event.OrganiserType.CAMPUS_IG:
        from db.user import MentorScopeGrant
        from api.dashboard.mentor.dash_mentor_helper import has_scope
        is_campus_mentor = has_scope(
            user_id, MentorScopeGrant.ScopeType.CAMPUS_MENTOR, event.scope_org_id
        )
    elif event.organiser_type == Event.OrganiserType.GLOBAL_IG:
        from db.user import MentorScopeGrant
        from db.task import UserIgLink
        from api.dashboard.mentor.dash_mentor_helper import get_scope_ids
        is_ig_mentor_assigned = bool(
            get_scope_ids(user_id, MentorScopeGrant.ScopeType.IG_MENTOR)
        ) and UserIgLink.objects.filter(
            user_id=user_id,
            ig_id=event.organiser_ig_id,
            assignment_type=UserIgLink.AssignmentType.MENTOR,
            is_active=True
        ).exists()
    elif event.organiser_type == Event.OrganiserType.COMPANY:
        from db.company import Company
        from api.dashboard.company.company_views import is_company_owner_or_admin
        company = Company.objects.filter(
            org_id=event.organiser_org_id, status='verified'
        ).first()
        is_company_owner = is_company_owner_or_admin(user_id, company)

    return is_campus_authority, is_campus_mentor, is_ig_mentor_assigned, is_company_owner


def _resolve_creator_campus_id(user_id):
    """Return the College org id (campus) the given user belongs to, or None.

    Prefers an approved Campus Mentor's scoped org, otherwise falls back to the
    user's College organisation link. Used to stamp the owning campus
    (scope_org) onto Campus IG events, which the create wizard does not send.
    """
    from db.user import MentorScopeGrant
    from api.dashboard.mentor.dash_mentor_helper import get_scope_ids
    campus_org_ids = get_scope_ids(user_id, MentorScopeGrant.ScopeType.CAMPUS_MENTOR)
    if campus_org_ids:
        return next(iter(campus_org_ids))

    from db.organization import UserOrganizationLink
    from utils.types import OrganizationType
    link = UserOrganizationLink.objects.filter(
        user_id=user_id,
        org__org_type=OrganizationType.COLLEGE.value,
    ).first()
    return link.org_id if link else None


# ─────────────────────────────────────────────────────────────────────────────
# MANAGE EVENT LIST + CREATE
# ─────────────────────────────────────────────────────────────────────────────

class ManageEventListCreateAPI(APIView):
    """
    GET  /events/manage/   → events the caller can manage
    POST /events/manage/   → create a new event
    """
    authentication_classes = [CustomizePermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve Manage Event List Create.",
        responses={200: EventListItemSerializer},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        is_admin = RoleType.ADMIN.value in roles

        if is_admin:
            # Admins can view/edit all events (excluding drafts) from the manage list.
            events = _get_manageable_events().exclude(status=Event.Status.DRAFT)
        else:
            # Events created by the user + events where user is co_owner
            co_owned_event_ids = list(
                EventConnection.objects.filter(
                    entity_type=EventConnection.EntityType.CO_OWNER,
                    entity_id=user_id,
                ).values_list('event_id', flat=True)
            )

            q_filter = Q(created_by_id=user_id) | Q(id__in=co_owned_event_ids)
            
            # Allow Company and Company Mentors to see all events for their company
            if RoleType.COMPANY.value in roles or RoleType.MENTOR.value in roles:
                company_org_ids = _get_user_company_org_ids(user_id, roles)
                if company_org_ids:
                    q_filter |= Q(
                        organiser_type=Event.OrganiserType.COMPANY.value,
                        organiser_org_id__in=company_org_ids
                    )

            # Use _get_manageable_events() so cancelled events remain visible to their owner
            events = _get_manageable_events().filter(q_filter)

        # Optional status filter & Queue Scoping
        if status := request.query_params.get('status'):
            if not is_admin:
                if status == Event.Status.PENDING_MENTOR_APPROVAL and RoleType.MENTOR.value in roles:
                    # A mentor can hold multiple tiers simultaneously (grants
                    # are additive) — union the pending-approval queues for
                    # every tier they actually hold, instead of picking one
                    # arbitrary tier via .first().                    from django.db.models import Q as _Q
                    from db.user import MentorScopeGrant
                    from db.task import UserIgLink
                    from api.dashboard.mentor.dash_mentor_helper import get_scope_ids

                    campus_org_ids = get_scope_ids(user_id, MentorScopeGrant.ScopeType.CAMPUS_MENTOR)
                    user_ig_ids = list(
                        UserIgLink.objects.filter(
                            user_id=user_id,
                            assignment_type=UserIgLink.AssignmentType.MENTOR,
                            is_active=True
                        ).values_list('ig_id', flat=True)
                    )

                    scope_filter = Q()
                    has_any_scope = False
                    if campus_org_ids:
                        scope_filter |= Q(
                            organiser_type=Event.OrganiserType.CAMPUS_IG,
                            scope_org_id__in=campus_org_ids,
                        )
                        has_any_scope = True
                    if user_ig_ids:
                        scope_filter |= Q(
                            organiser_type=Event.OrganiserType.GLOBAL_IG,
                            organiser_ig_id__in=user_ig_ids,
                        )
                        has_any_scope = True

                    if has_any_scope:
                        events = _get_manageable_events().filter(status=status).filter(scope_filter)
                    else:
                        events = _get_manageable_events().none()
                elif status == Event.Status.PENDING_CAMPUS_APPROVAL and bool(set(roles) & {RoleType.CAMPUS_LEAD.value, RoleType.ZONAL_CAMPUS_LEAD.value, RoleType.DISTRICT_CAMPUS_LEAD.value}):
                    from db.organization import UserOrganizationLink
                    user_org_ids = UserOrganizationLink.objects.filter(user_id=user_id).values_list('org_id', flat=True)
                    events = _get_manageable_events().filter(
                        status=status,
                        scope_org_id__in=user_org_ids
                    )
                else:
                    events = events.filter(status=status)
            else:
                events = events.filter(status=status)

        paginated = CommonUtils.get_paginated_queryset(
            events.select_related('category', 'organiser_ig', 'organiser_org'), request,
            search_fields=['title', 'venue_city'],
            sort_fields={'created_at': 'created_at', 'start_datetime': 'start_datetime'},
        )
        serializer = EventListItemSerializer(
            paginated['queryset'], many=True,
            context={'user_id': user_id, 'request': request},
        )
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Create Manage Event List Create.",
        request=EventWriteSerializer,
        responses={200: EventDetailSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        if not _can_create_event(roles):
            return CustomResponse(
                general_message='You do not have permission to create events.'
            ).get_failure_response()

        # Enforce Mentor Creation Scopes
        if RoleType.MENTOR.value in roles and not (set(roles) & MANAGEABLE_ROLES - {RoleType.MENTOR.value}):
            # User is ONLY a mentor. A mentor can hold multiple tiers
            # simultaneously (grants are additive) — check the requested
            # organiser_type against whichever scopes they actually hold,
            # instead of pinning them to one arbitrary tier via .first().
            from db.user import MentorScopeGrant
            from api.dashboard.mentor.dash_mentor_helper import get_mentor_scopes
            scopes = get_mentor_scopes(user_id)
            if not scopes:
                return CustomResponse(general_message='Active mentor profile not found.').get_failure_response()

            has_campus = any(st == MentorScopeGrant.ScopeType.CAMPUS_MENTOR for st, _ in scopes)
            has_company = any(st == MentorScopeGrant.ScopeType.COMPANY_MENTOR for st, _ in scopes)
            has_ig = any(st == MentorScopeGrant.ScopeType.IG_MENTOR for st, _ in scopes)

            payload_organiser_type = request.data.get('organiser_type')

            if payload_organiser_type == Event.OrganiserType.CAMPUS_IG.value:
                if not has_campus:
                    return CustomResponse(general_message='Campus Mentors can only create Campus IG events.').get_failure_response()
            elif payload_organiser_type == Event.OrganiserType.COMPANY.value:
                if not has_company:
                    return CustomResponse(general_message='Company Mentors can only create Company events.').get_failure_response()
            elif payload_organiser_type == Event.OrganiserType.GLOBAL_IG.value:
                if not has_ig:
                    return CustomResponse(general_message='IG Mentors can only create Global IG events.').get_failure_response()
                # Verify that the IG being requested is one they mentor
                payload_organiser_ig = request.data.get('organiser_ig')
                if not payload_organiser_ig:
                    return CustomResponse(general_message='organiser_ig is required.').get_failure_response()
                from db.task import UserIgLink
                is_assigned = UserIgLink.objects.filter(
                    user_id=user_id,
                    ig_id=payload_organiser_ig,
                    assignment_type=UserIgLink.AssignmentType.MENTOR,
                    is_active=True
                ).exists()
                if not is_assigned:
                    return CustomResponse(general_message='You are not authorized to create events for this Interest Group.').get_failure_response()
            else:
                return CustomResponse(general_message='This mentor tier is not authorized to create events yet.').get_failure_response()

        payload, new_media_paths, merge_error = merge_event_write_payload(
            request, partial=False, event=None,
        )
        if merge_error:
            delete_event_media_paths(new_media_paths)
            return CustomResponse(general_message=merge_error).get_failure_response()

        # save_uploaded_event_image/fetch_event_image_from_url above already
        # wrote any new cover/banner to disk. `committed` only flips to True
        # right before the one success return below -- every other exit from
        # here on (a validation failure, an unhandled exception) must clean
        # those files up, or they orphan under MEDIA_ROOT with nothing in the
        # DB pointing at them.
        committed = False
        try:
            # Enforce organiser_org for Company events
            if payload.get('organiser_type') == Event.OrganiserType.COMPANY.value:
                payload_organiser_org = payload.get('organiser_org')
                if not payload_organiser_org:
                    return CustomResponse(general_message='organiser_org is required for Company events.').get_failure_response()

                if RoleType.ADMIN.value not in roles:
                    valid_org_ids = set(_get_user_company_org_ids(user_id, roles))
                    if str(payload_organiser_org) not in [str(o) for o in valid_org_ids]:
                        return CustomResponse(general_message='You are not authorized to create events for this company.').get_failure_response()

                # PRD §15 — rate/abuse limit: cap how many not-yet-published
                # company events can be open at once, mirroring
                # job_views.MAX_PENDING_JOBS_PER_MENTOR.
                open_count = _get_manageable_events().filter(
                    organiser_type=Event.OrganiserType.COMPANY,
                    organiser_org_id=payload_organiser_org,
                    status__in=[
                        Event.Status.DRAFT, Event.Status.PENDING_MENTOR_APPROVAL, Event.Status.PENDING_APPROVAL,
                    ],
                ).count()
                if open_count >= MAX_OPEN_COMPANY_EVENTS:
                    return CustomResponse(
                        general_message=f'This company already has {MAX_OPEN_COMPANY_EVENTS} draft/pending-approval events. Resolve those before creating more.'
                    ).get_failure_response(status_code=429)

            # Enforce campus tenancy for Campus events
            ownership_error = _validate_campus_event_ownership(
                user_id, roles,
                payload.get('organiser_type'),
                payload.get('organiser_org'),
            )
            if ownership_error:
                return CustomResponse(general_message=ownership_error).get_failure_response()

            # Campus IG events: stamp the owning campus (scope_org) from the creator.
            # The wizard only sends the IG (scope_ci_id); the campus is implicit and
            # required downstream for mentor/campus approval routing and scoping.
            # Non-admins are pinned to their own campus (blocks cross-campus
            # targeting); admins may target a campus explicitly via scope_org.
            if payload.get('organiser_type') == Event.OrganiserType.CAMPUS_IG.value:
                if RoleType.ADMIN.value in roles:
                    if not payload.get('scope_org'):
                        payload['scope_org'] = _resolve_creator_campus_id(user_id)
                else:
                    campus_id = _resolve_creator_campus_id(user_id)
                    if not campus_id:
                        return CustomResponse(
                            general_message='You are not associated with a campus.'
                        ).get_failure_response()
                    payload['scope_org'] = campus_id

            serializer = EventWriteSerializer(
                data=payload,
                context={'user_id': user_id},
            )
            if not serializer.is_valid():
                return CustomResponse(
                    general_message=serializer.errors,
                ).get_failure_response()

            event = serializer.save()
            committed = True

            return CustomResponse(
                general_message='Event created successfully.',
                response=EventDetailSerializer(
                    event, context={'user_id': user_id, 'request': request},
                ).data,
            ).get_success_response()
        finally:
            if not committed:
                delete_event_media_paths(new_media_paths)


# ─────────────────────────────────────────────────────────────────────────────
# MANAGE EVENT DETAIL (GET / PUT / PATCH / DELETE)
# ─────────────────────────────────────────────────────────────────────────────

class ManageEventDetailAPI(APIView):
    """
    GET    /events/manage/<event_id>/  → full detail + edit history
    PUT    /events/manage/<event_id>/  → full update
    PATCH  /events/manage/<event_id>/  → partial update
    DELETE /events/manage/<event_id>/  → soft cancel
    """
    authentication_classes = [CustomizePermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _get_managed_event(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        # Use _get_manageable_events() so managers can see/edit their cancelled events
        event = _get_manageable_events().filter(id=event_id).first()
        if not event:
            return None, None, None, 'Event not found.'
        is_admin = RoleType.ADMIN.value in roles
        if not is_admin and not can_manage_event(user_id, event):
            return None, None, None, 'You do not have permission to manage this event.'
        return event, user_id, roles, None

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve Manage Event Detail.",
        responses={200: EventDetailSerializer},
    )
    def get(self, request, event_id):
        event, user_id, _, error = self._get_managed_event(request, event_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response()

        logs = EventLog.objects.filter(event=event).order_by('-edited_at')
        event_data = EventDetailSerializer(
            event,
            context={
                'user_id': user_id, 'is_manage_view': True, 'request': request,
            },
        ).data
        event_data['edit_history'] = EventLogSerializer(logs, many=True).data

        return CustomResponse(
            general_message='Event detail retrieved.',
            response=event_data,
        ).get_success_response()

    @extend_schema(tags=['Dashboard - Events'], description="Update Manage Event Detail.",
        responses={200: EventDetailSerializer},
    )
    def put(self, request, event_id):
        return self._update(request, event_id, partial=False)

    @extend_schema(tags=['Dashboard - Events'], description="Partially update Manage Event Detail.",
        responses={200: EventDetailSerializer},
    )
    def patch(self, request, event_id):
        return self._update(request, event_id, partial=True)

    def _update(self, request, event_id, partial):
        event, user_id, _, error = self._get_managed_event(request, event_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response()

        if not is_editable(event.status):
            return CustomResponse(
                general_message=f'Cannot edit a {event.status} event.'
            ).get_failure_response()

        old_cover = event.cover_image
        old_banner = event.banner_image

        payload, new_media_paths, merge_error = merge_event_write_payload(
            request, partial=partial, event=event,
        )
        if merge_error:
            delete_event_media_paths(new_media_paths)
            return CustomResponse(general_message=merge_error).get_failure_response()

        # save_uploaded_event_image/fetch_event_image_from_url above already
        # wrote any new cover/banner to disk. `committed` only flips to True
        # right before the one success return below -- every other exit from
        # here on (a validation failure, a rolled-back transaction, an
        # unhandled exception) must clean those files up, or they orphan
        # under MEDIA_ROOT with nothing in the DB pointing at them.
        committed = False
        try:
            # Enforce Mentor Update Scopes
            roles = JWTUtils.fetch_role(request)
            if RoleType.MENTOR.value in roles and not (set(roles) & MANAGEABLE_ROLES - {RoleType.MENTOR.value}):
                # User is ONLY a mentor. Check the requested organiser_type
                # against whichever scopes they actually hold (multi-tier
                # mentors can manage events for any tier they hold), instead of
                # pinning them to one arbitrary tier via .first().
                from db.user import MentorScopeGrant
                from api.dashboard.mentor.dash_mentor_helper import get_mentor_scopes
                scopes = get_mentor_scopes(user_id)
                if not scopes:
                    return CustomResponse(general_message='Active mentor profile not found.').get_failure_response()

                has_campus = any(st == MentorScopeGrant.ScopeType.CAMPUS_MENTOR for st, _ in scopes)
                has_company = any(st == MentorScopeGrant.ScopeType.COMPANY_MENTOR for st, _ in scopes)
                has_ig = any(st == MentorScopeGrant.ScopeType.IG_MENTOR for st, _ in scopes)

                payload_organiser_type = payload.get('organiser_type', event.organiser_type)

                if payload_organiser_type == Event.OrganiserType.CAMPUS_IG.value:
                    if not has_campus:
                        return CustomResponse(general_message='Campus Mentors can only manage Campus IG events.').get_failure_response()
                elif payload_organiser_type == Event.OrganiserType.COMPANY.value:
                    if not has_company:
                        return CustomResponse(general_message='Company Mentors can only manage Company events.').get_failure_response()
                elif payload_organiser_type == Event.OrganiserType.GLOBAL_IG.value:
                    if not has_ig:
                        return CustomResponse(general_message='IG Mentors can only manage Global IG events.').get_failure_response()
                    # Verify that the IG being updated/requested is one they mentor
                    payload_organiser_ig = payload.get('organiser_ig', event.organiser_ig_id)
                    if not payload_organiser_ig:
                        return CustomResponse(general_message='organiser_ig is required.').get_failure_response()
                    from db.task import UserIgLink
                    is_assigned = UserIgLink.objects.filter(
                        user_id=user_id,
                        ig_id=payload_organiser_ig,
                        assignment_type=UserIgLink.AssignmentType.MENTOR,
                        is_active=True
                    ).exists()
                    if not is_assigned:
                        return CustomResponse(general_message='You are not authorized to manage events for this Interest Group.').get_failure_response()
                else:
                    return CustomResponse(general_message='This mentor tier is not authorized to manage events yet.').get_failure_response()

            # Enforce organiser_org for Company events
            if payload.get('organiser_type', event.organiser_type) == Event.OrganiserType.COMPANY.value:
                payload_organiser_org = payload.get('organiser_org', event.organiser_org_id)
                if not payload_organiser_org:
                    return CustomResponse(general_message='organiser_org is required for Company events.').get_failure_response()

                if RoleType.ADMIN.value not in roles:
                    valid_org_ids = set(_get_user_company_org_ids(user_id, roles))
                    if str(payload_organiser_org) not in [str(o) for o in valid_org_ids]:
                        return CustomResponse(general_message='You are not authorized to manage events for this company.').get_failure_response()

            # Enforce campus tenancy for Campus events
            ownership_error = _validate_campus_event_ownership(
                user_id, roles,
                payload.get('organiser_type', event.organiser_type),
                payload.get('organiser_org', event.organiser_org_id),
            )
            if ownership_error:
                return CustomResponse(general_message=ownership_error).get_failure_response()

            # Campus IG events: keep scope_org pinned to the owning campus (derived
            # from the original creator). Prevents tampering and backfills legacy
            # events that were created without a campus.
            effective_organiser_type = payload.get('organiser_type', event.organiser_type)
            if effective_organiser_type == Event.OrganiserType.CAMPUS_IG.value:
                campus_id = _resolve_creator_campus_id(event.created_by_id)
                if campus_id:
                    payload['scope_org'] = campus_id

            serializer = EventWriteSerializer(
                event, data=payload,
                partial=partial,
                context={'user_id': user_id},
            )
            if not serializer.is_valid():
                return CustomResponse(general_message=serializer.errors).get_failure_response()

            # `status` isn't a writable field on EventWriteSerializer, so an edit
            # that reschedules a live event's dates leaves its lifecycle status
            # stale (e.g. a COMPLETED event moved back into the future would stay
            # COMPLETED forever, hidden from active feeds and interest actions).
            # Re-settle it against the clock — events still in the approval
            # pipeline (draft/pending/cancelled) are untouched.
            #
            # Forward drift (published -> ongoing -> completed, as real time
            # passes) needs no re-approval: it doesn't grant anything the editor
            # didn't already have. A REVIVAL — dates pushed out so a completed or
            # ongoing event becomes published/ongoing again — is different: it
            # must be routed through the same organiser-authority check a fresh
            # publish would use, not assumed to still carry whatever approval it
            # had at some point in the past. Otherwise editing dates becomes a
            # way to relaunch an event live without renewed review (e.g. a
            # company owner rescheduling a completed event straight back to
            # PUBLISHED, bypassing the admin sign-off a fresh publish requires).
            #
            # Both writes below must land together: if the resettle save failed
            # after the field save committed, a revived event would sit at its
            # old terminal status (e.g. COMPLETED) with future dates instead of
            # either its old state or its correctly re-routed one.
            with transaction.atomic():
                serializer.save()

                _TERMINAL_ORDER = {Event.Status.PUBLISHED: 0, Event.Status.ONGOING: 1, Event.Status.COMPLETED: 2}
                if event.status in _TERMINAL_ORDER:
                    resettled_status = resolve_terminal_status(event, Event.Status.PUBLISHED)
                    if _TERMINAL_ORDER[resettled_status] < _TERMINAL_ORDER[event.status]:
                        is_campus_authority, is_campus_mentor, is_ig_mentor_assigned, is_company_owner = \
                            _resolve_publish_authority(user_id, roles, event)
                        resettled_status = resolve_terminal_status(event, decide_publish_status(
                            organiser_type=event.organiser_type,
                            scope=event.scope,
                            is_admin=RoleType.ADMIN.value in roles,
                            is_campus_authority=is_campus_authority,
                            is_campus_mentor=is_campus_mentor,
                            is_ig_mentor_assigned=is_ig_mentor_assigned,
                            is_company_owner=is_company_owner,
                        ))
                    if resettled_status != event.status:
                        event.status = resettled_status
                        event.save(update_fields=['status'])

            committed = True

            delete_stale_event_media(old_cover, event.cover_image)
            delete_stale_event_media(old_banner, event.banner_image)

            return CustomResponse(
                general_message='Event updated successfully.',
                response=EventDetailSerializer(
                    event, context={'user_id': user_id, 'request': request},
                ).data,
            ).get_success_response()
        finally:
            if not committed:
                delete_event_media_paths(new_media_paths)

    @extend_schema(tags=['Dashboard - Events'], description="Delete Manage Event Detail.",
        responses={200: EventDetailSerializer},
    )
    def delete(self, request, event_id):
        event, user_id, _, error = self._get_managed_event(request, event_id)
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

        # Broadcast cancellation to all users who expressed interest.
        # url is intentionally None — the event page is no longer valid.
        actor = User.objects.filter(id=user_id).first()
        if actor:
            BroadcastUtils.create_broadcast(
                title='Event Cancelled',
                description=f'The event "{event.title}" has been cancelled.',
                target_type='event_interest',
                target_id=event.id,
                created_by=actor,
                expiry_key='event_cancelled',
                url=None,
            )

        # Nullify the deep-link URL on all existing broadcast and direct
        # notifications that pointed to this event's page. The page is no
        # longer valid after cancellation.
        event_url = f'/events/{event.id}/'
        from db.notification import Notification as DirectNotification, BroadcastNotification
        BroadcastNotification.objects.filter(url=event_url).update(url=None)
        DirectNotification.objects.filter(url=event_url).update(url=None)

        return CustomResponse(
            general_message='Event has been cancelled.',
            response={'id': event.id, 'status': Event.Status.CANCELLED},
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# PUBLISH
# ─────────────────────────────────────────────────────────────────────────────

class ManageEventPublishAPI(APIView):
    """
    POST /events/manage/<event_id>/publish/
    Transitions a draft event into the approval pipeline.
    """
    authentication_classes = [CustomizePermission]

    REQUIRED_FIELDS = [
        'title', 'description', 'start_datetime', 'end_datetime',
        'venue_type', 'organiser_type',
    ]

    @extend_schema(tags=['Dashboard - Events'], description="Create Manage Event Publish.",
        responses={200: inline_serializer(
            name='EventPublishResponse',
            fields={
                'id': s.CharField(),
                'status': s.CharField(),
            },
        )},
    )
    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()

        if not (RoleType.ADMIN.value in roles or can_manage_event(user_id, event)):
            return CustomResponse(
                general_message='You do not have permission to manage this event.'
            ).get_failure_response()

        if event.status not in (Event.Status.DRAFT, Event.Status.REJECTED):
            return CustomResponse(
                general_message=f'Only draft or rejected events can be published (current: {event.status}).'
            ).get_failure_response()

        # Validate required fields are filled
        missing = [f for f in self.REQUIRED_FIELDS if not getattr(event, f, None)]
        if missing:
            return CustomResponse(
                general_message=f'Cannot publish: missing fields: {", ".join(missing)}.'
            ).get_failure_response()

        # Resolve the caller's standing for whichever organiser this event has,
        # then let the policy decide. Past-dated events are allowed through:
        # resolve_terminal_status settles them against the clock below.
        is_campus_authority, is_campus_mentor, is_ig_mentor_assigned, is_company_owner = \
            _resolve_publish_authority(user_id, roles, event)

        new_status = resolve_terminal_status(event, decide_publish_status(
            organiser_type=event.organiser_type,
            scope=event.scope,
            is_admin=RoleType.ADMIN.value in roles,
            is_campus_authority=is_campus_authority,
            is_campus_mentor=is_campus_mentor,
            is_ig_mentor_assigned=is_ig_mentor_assigned,
            is_company_owner=is_company_owner,
        ))

        old_status = event.status
        event.status = new_status
        event.updated_by_id = user_id
        event.save()

        log_event_action(
            event=event,
            user_id=user_id,
            action=EventLog.Action.PUBLISHED,
            changes={'Status': {'from': old_status, 'to': new_status}},
            details={'new_status': new_status},
        )

        # Announce the event when it goes live without a review stage. A
        # backdated event resolves straight to COMPLETED and is not announced.
        if should_announce(new_status):
            actor = User.objects.filter(id=user_id).first()
            if actor:
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
                    # ADMIN / COMPANY / fallback → global broadcast
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
            general_message=f'Event submitted: status is now "{new_status}".',
            response={'id': event.id, 'status': new_status},
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# CO-OWNERS
# ─────────────────────────────────────────────────────────────────────────────

class ManageEventCoOwnerAPI(APIView):
    """
    GET  /events/manage/<event_id>/co-owners/
    POST /events/manage/<event_id>/co-owners/
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve Manage Event Co Owner.",
        responses={200: EventCoOwnerSerializer},
    )
    def get(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()
        # Admins can manage co-owners for any event.
        if not (RoleType.ADMIN.value in roles or can_manage_event(user_id, event)):
            return CustomResponse(
                general_message='Permission denied.'
            ).get_failure_response()

        co_owners = list(event.connections.filter(entity_type=EventConnection.EntityType.CO_OWNER).select_related('created_by'))
        user_ids = [c.entity_id for c in co_owners]
        users = {str(u.id): u for u in User.objects.filter(id__in=user_ids)}

        return CustomResponse(
            general_message='Co-owners retrieved.',
            response=EventCoOwnerSerializer(co_owners, many=True, context={'users_map': users}).data,
        ).get_success_response()

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Create Manage Event Co Owner.",
        responses={200: EventCoOwnerSerializer},
    )
    def post(self, request, event_id):
        """
        Body: { "user_id": "<uuid>" }
        Adds a single user as a co-owner.
        """
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()
        # Admins can manage co-owners for any event.
        if not (RoleType.ADMIN.value in roles or can_manage_event(user_id, event)):
            return CustomResponse(general_message='Permission denied.').get_failure_response()

        target_user_id = request.data.get('user_id')
        if not target_user_id:
            return CustomResponse(general_message='user_id is required.').get_failure_response()

        if not User.objects.filter(id=target_user_id).exists():
            return CustomResponse(general_message='User not found.').get_failure_response()

        if target_user_id == event.created_by_id:
            return CustomResponse(
                general_message='The event creator is already the owner.'
            ).get_failure_response()

        conn, created = EventConnection.objects.get_or_create(
            event=event,
            entity_id=target_user_id,
            entity_type=EventConnection.EntityType.CO_OWNER,
            defaults={
                'id': str(uuid.uuid4()),
                'created_by_id': user_id,
                'updated_by_id': user_id,
            },
        )

        if not created:
            return CustomResponse(
                general_message='User is already a co-owner.'
            ).get_failure_response()

        # Resolve co-owner's name for the log
        co_owner_user = User.objects.filter(id=target_user_id).first()
        log_event_action(
            event=event,
            user_id=user_id,
            action=EventLog.Action.CO_OWNER_ADDED,
            details={
                'name': co_owner_user.full_name if co_owner_user else target_user_id,
                'muid': co_owner_user.muid if co_owner_user else None,
                'user_id': target_user_id,
            },
        )

        return CustomResponse(
            general_message='Co-owner added.',
            response=EventCoOwnerSerializer(conn).data,
        ).get_success_response()


class ManageEventCoOwnerRemoveAPI(APIView):
    """
    DELETE /events/manage/<event_id>/co-owners/<co_owner_id>/
    Removes a co-owner row (co_owner_id = EventConnection.id).
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Events'], description="Delete Manage Event Co Owner Remove.",
        responses={200: EventCoOwnerSerializer},
    )
    def delete(self, request, event_id, co_owner_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()
        # Admins can manage co-owners for any event.
        if not (RoleType.ADMIN.value in roles or can_manage_event(user_id, event)):
            return CustomResponse(general_message='Permission denied.').get_failure_response()

        conn = EventConnection.objects.filter(
            id=co_owner_id,
            event=event,
            entity_type=EventConnection.EntityType.CO_OWNER,
        ).first()
        if not conn:
            return CustomResponse(general_message='Co-owner record not found.').get_failure_response()

        # Resolve co-owner's name before deleting
        co_owner_user = User.objects.filter(id=conn.entity_id).first()
        conn.delete()

        log_event_action(
            event=event,
            user_id=user_id,
            action=EventLog.Action.CO_OWNER_REMOVED,
            details={
                'name': co_owner_user.full_name if co_owner_user else conn.entity_id,
                'muid': co_owner_user.muid if co_owner_user else None,
                'user_id': conn.entity_id,
            },
        )
        return CustomResponse(general_message='Co-owner removed.').get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# COLLABORATORS
# ─────────────────────────────────────────────────────────────────────────────

COLLAB_TYPES = [
    EventConnection.EntityType.COLLAB_IG,
    EventConnection.EntityType.COLLAB_CAMPUS,
    EventConnection.EntityType.COLLAB_CAMPUS_IG,
    EventConnection.EntityType.COLLAB_COMPANY,
]


def _resolve_entity_name(entity_type, entity_id):
    """
    Return a human-readable name for a collaborator entity.
    Used to populate the 'name' field in log details.
    """
    try:
        if entity_type == EventConnection.EntityType.COLLAB_IG:
            from db.task import InterestGroup
            ig = InterestGroup.objects.filter(id=entity_id).first()
            return ig.name if ig else entity_id
        elif entity_type in (
            EventConnection.EntityType.COLLAB_CAMPUS,
            EventConnection.EntityType.COLLAB_COMPANY,
        ):
            from db.organization import Organization
            org = Organization.objects.filter(id=entity_id).first()
            return org.title if org else entity_id
        elif entity_type == EventConnection.EntityType.COLLAB_CAMPUS_IG:
            return f'Campus-IG ({entity_id})'
    except Exception:
        pass
    return entity_id


def _get_entity_leads(entity_type, entity_id):
    """
    Return the User objects that are the leads/contacts of a collaborator entity.
    Used to send direct invite notifications to the right people.
    """
    leads = []
    try:
        if entity_type == EventConnection.EntityType.COLLAB_IG:
            from db.task import UserIgLink
            ig_lead_links = UserIgLink.objects.filter(
                ig_id=entity_id,
                assignment_type=UserIgLink.AssignmentType.LEAD,
                is_active=True,
            ).select_related('user')
            leads = [link.user for link in ig_lead_links]
        elif entity_type in (
            EventConnection.EntityType.COLLAB_CAMPUS,
            EventConnection.EntityType.COLLAB_COMPANY,
        ):
            from db.organization import UserOrganizationLink
            # Only notify the org's leads (Campus Lead / Company), not every member.
            lead_links = UserOrganizationLink.objects.filter(
                org_id=entity_id,
                verified=True,
                user__user_role_link_user__role__title__in=[
                    RoleType.CAMPUS_LEAD.value,
                    RoleType.COMPANY.value,
                ],
            ).select_related('user').distinct()
            leads = [link.user for link in lead_links]
    except Exception:
        pass
    return leads


def _caller_can_respond(conn, user_id, roles):
    """
    Returns True if `user_id` is an authorised lead for the entity being invited.
    Used by both Accept and Reject views.
    """
    from db.organization import UserOrganizationLink
    if RoleType.ADMIN.value in roles:
        return True
    if conn.entity_type == EventConnection.EntityType.COLLAB_IG:
        from db.task import InterestGroup
        ig = InterestGroup.objects.filter(id=conn.entity_id).first()
        if ig:
            return f'{ig.code} IGLead' in roles
    elif conn.entity_type == EventConnection.EntityType.COLLAB_CAMPUS:
        in_org = UserOrganizationLink.objects.filter(
            user_id=user_id, org_id=conn.entity_id, verified=True
        ).exists()
        return in_org and RoleType.CAMPUS_LEAD.value in roles
    elif conn.entity_type == EventConnection.EntityType.COLLAB_COMPANY:
        in_org = UserOrganizationLink.objects.filter(
            user_id=user_id, org_id=conn.entity_id, verified=True
        ).exists()
        return in_org and RoleType.COMPANY.value in roles
    elif conn.entity_type == EventConnection.EntityType.COLLAB_CAMPUS_IG:
        # entity_id is the InterestGroup id; require the matching IG campus-lead role
        from db.task import InterestGroup
        ig = InterestGroup.objects.filter(id=conn.entity_id).first()
        if ig:
            return f'{ig.code} CampusLead' in roles
    return False


class ManageEventCollaboratorAPI(APIView):
    """
    GET  /events/manage/<event_id>/collaborators/  → all invites (incl. pending/rejected)
    POST /events/manage/<event_id>/collaborators/  → invite a new collaborator
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve Manage Event Collaborator.",
        responses={200: EventCollaboratorSerializer},
    )
    def get(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()
        # Admins can manage collaborators for any event.
        if not (RoleType.ADMIN.value in roles or can_manage_event(user_id, event)):
            return CustomResponse(general_message='Permission denied.').get_failure_response()

        collabs = list(event.connections.filter(entity_type__in=COLLAB_TYPES))
        ig_ids = [c.entity_id for c in collabs if c.entity_type == EventConnection.EntityType.COLLAB_IG]
        org_ids = [c.entity_id for c in collabs if c.entity_type in (EventConnection.EntityType.COLLAB_CAMPUS, EventConnection.EntityType.COLLAB_COMPANY)]

        from db.task import InterestGroup
        from db.organization import Organization
        igs = {str(ig.id): ig for ig in InterestGroup.objects.filter(id__in=ig_ids)}
        orgs = {str(org.id): org for org in Organization.objects.filter(id__in=org_ids)}

        return CustomResponse(
            general_message='Collaborators retrieved.',
            response=EventCollaboratorSerializer(
                collabs, many=True,
                context={'request': request, 'igs_map': igs, 'orgs_map': orgs}
            ).data,
        ).get_success_response()

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Create Manage Event Collaborator.",
        responses={200: EventCollaboratorSerializer},
    )
    def post(self, request, event_id):
        """
        Body: {
          "entity_type": "collab_ig" | "collab_campus" | "collab_campus_ig" | "collab_company",
          "entity_id": "<uuid>",
          "role_label": "Venue Partner"  (optional)
        }
        """
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()
        # Admins can manage collaborators for any event.
        if not (RoleType.ADMIN.value in roles or can_manage_event(user_id, event)):
            return CustomResponse(general_message='Permission denied.').get_failure_response()

        entity_type = request.data.get('entity_type')
        entity_id = request.data.get('entity_id')
        role_label = request.data.get('role_label', '')

        if entity_type not in [t.value for t in COLLAB_TYPES]:
            return CustomResponse(
                general_message=f'Invalid entity_type. Must be one of: {", ".join(t.value for t in COLLAB_TYPES)}'
            ).get_failure_response()

        if not entity_id:
            return CustomResponse(general_message='entity_id is required.').get_failure_response()

        conn, created = EventConnection.objects.get_or_create(
            event=event,
            entity_type=entity_type,
            entity_id=entity_id,
            defaults={
                'id': str(uuid.uuid4()),
                'invite_status': EventConnection.InviteStatus.PENDING,
                'role_label': role_label,
                'created_by_id': user_id,
                'updated_by_id': user_id,
            },
        )

        if not created:
            return CustomResponse(
                general_message='This entity has already been invited.'
            ).get_failure_response()

        # Resolve entity name for the log
        entity_name = _resolve_entity_name(entity_type, entity_id)
        log_event_action(
            event=event,
            user_id=user_id,
            action=EventLog.Action.COLLAB_INVITED,
            details={
                'entity_type': entity_type,
                'entity_id':   entity_id,
                'name':        entity_name,
                'role_label':  role_label or None,
            },
        )

        return CustomResponse(
            general_message='Collaborator invited.',
            response=EventCollaboratorSerializer(conn).data,
        ).get_success_response()


class ManageEventCollaboratorRemoveAPI(APIView):
    """
    DELETE /events/manage/<event_id>/collaborators/<collaborator_id>/
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Events'], description="Delete Manage Event Collaborator Remove.",
        responses={200: EventCollaboratorSerializer},
    )
    def delete(self, request, event_id, collaborator_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()
        # Admins can manage collaborators for any event.
        if not (RoleType.ADMIN.value in roles or can_manage_event(user_id, event)):
            return CustomResponse(general_message='Permission denied.').get_failure_response()

        conn = EventConnection.objects.filter(
            id=collaborator_id,
            event=event,
            entity_type__in=COLLAB_TYPES,
        ).first()
        if not conn:
            return CustomResponse(general_message='Collaborator not found.').get_failure_response()

        entity_name = _resolve_entity_name(conn.entity_type, conn.entity_id)
        conn.delete()

        log_event_action(
            event=event,
            user_id=user_id,
            action=EventLog.Action.COLLAB_REMOVED,
            details={
                'entity_type': conn.entity_type,
                'entity_id':   conn.entity_id,
                'name':        entity_name,
            },
        )
        return CustomResponse(general_message='Collaborator removed.').get_success_response()


class ManageEventCollaboratorAcceptAPI(APIView):
    """
    POST /events/manage/<event_id>/collaborators/<collaborator_id>/accept/
    Called by the lead of the invited entity to accept the collaboration invite.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Create Manage Event Collaborator Accept.",
        responses={200: EventCollaboratorSerializer},
    )
    def post(self, request, event_id, collaborator_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()

        conn = EventConnection.objects.filter(
            id=collaborator_id,
            event=event,
            entity_type__in=COLLAB_TYPES,
        ).first()
        if not conn:
            return CustomResponse(general_message='Collaborator invite not found.').get_failure_response()

        if conn.invite_status != EventConnection.InviteStatus.PENDING:
            return CustomResponse(
                general_message=f'Invite is already {conn.invite_status}.'
            ).get_failure_response()

        # Verify the caller is an authorised lead for the invited entity
        if not _caller_can_respond(conn, user_id, roles):
            return CustomResponse(
                general_message='You are not authorised to accept this invite.'
            ).get_failure_response()

        conn.invite_status = EventConnection.InviteStatus.ACCEPTED
        conn.responded_at = timezone.now()
        conn.updated_by_id = user_id
        conn.save()

        entity_name = _resolve_entity_name(conn.entity_type, conn.entity_id)
        log_event_action(
            event=event,
            user_id=user_id,
            action=EventLog.Action.COLLAB_ACCEPTED,
            details={
                'entity_type': conn.entity_type,
                'entity_id':   conn.entity_id,
                'name':        entity_name,
            },
        )

        return CustomResponse(
            general_message='Collaboration accepted.',
            response=EventCollaboratorSerializer(conn).data,
        ).get_success_response()




class ManageEventCollaboratorRejectAPI(APIView):
    """
    POST /events/manage/<event_id>/collaborators/<collaborator_id>/reject/
    Called by the lead of the invited entity to reject. Body: { "reason": "..." }
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Create Manage Event Collaborator Reject.",
        responses={200: EventCollaboratorSerializer},
    )
    def post(self, request, event_id, collaborator_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()

        conn = EventConnection.objects.filter(
            id=collaborator_id,
            event=event,
            entity_type__in=COLLAB_TYPES,
        ).first()
        if not conn:
            return CustomResponse(general_message='Collaborator invite not found.').get_failure_response()

        if conn.invite_status != EventConnection.InviteStatus.PENDING:
            return CustomResponse(
                general_message=f'Invite is already {conn.invite_status}.'
            ).get_failure_response()

        if not _caller_can_respond(conn, user_id, roles):
            return CustomResponse(
                general_message='You are not authorised to reject this invite.'
            ).get_failure_response()

        conn.invite_status = EventConnection.InviteStatus.REJECTED
        conn.rejection_reason = request.data.get('reason', '')
        conn.responded_at = timezone.now()
        conn.updated_by_id = user_id
        conn.save()

        entity_name = _resolve_entity_name(conn.entity_type, conn.entity_id)
        log_event_action(
            event=event,
            user_id=user_id,
            action=EventLog.Action.COLLAB_REJECTED,
            details={
                'entity_type': conn.entity_type,
                'entity_id':   conn.entity_id,
                'name':        entity_name,
                'reason':      conn.rejection_reason,
            },
        )

        return CustomResponse(
            general_message='Collaboration invite rejected.',
            response=EventCollaboratorSerializer(conn).data,
        ).get_success_response()


class MyEventInvitesAPI(APIView):
    """
    GET /events/my-invites/
    Returns all pending event collaboration invites directed at entities the current user leads.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve My Event Invites.",
        responses={200: MyEventInviteSerializer},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        
        # If admin, fetch all pending collab invites globally
        if RoleType.ADMIN.value in roles:
            invites = EventConnection.objects.filter(
                invite_status=EventConnection.InviteStatus.PENDING,
                entity_type__in=COLLAB_TYPES
            ).select_related('event').order_by('-created_at')
            invites_list = list(invites)
            ig_ids = [inv.entity_id for inv in invites_list if inv.entity_type == EventConnection.EntityType.COLLAB_IG]
            org_ids = [inv.entity_id for inv in invites_list if inv.entity_type in (EventConnection.EntityType.COLLAB_CAMPUS, EventConnection.EntityType.COLLAB_COMPANY)]
            
            from db.task import InterestGroup
            from db.organization import Organization
            igs = {str(ig.id): ig for ig in InterestGroup.objects.filter(id__in=ig_ids)}
            orgs = {str(org.id): org for org in Organization.objects.filter(id__in=org_ids)}

            serializer = MyEventInviteSerializer(
                invites_list, many=True, context={'request': request, 'igs_map': igs, 'orgs_map': orgs},
            )
            return CustomResponse(
                general_message='Global pending invites retrieved.',
                response=serializer.data
            ).get_success_response()
            
        auth_ig_codes = []
        is_campus_lead = RoleType.CAMPUS_LEAD.value in roles
        is_company = RoleType.COMPANY.value in roles
        has_any_campus_lead_role = False
        
        for role in roles:
            if role.endswith(' IGLead'):
                ig_code = role.replace(' IGLead', '')
                auth_ig_codes.append(ig_code)
            if role.endswith(' CampusLead') or role == RoleType.CAMPUS_LEAD.value:
                has_any_campus_lead_role = True

        from db.task import InterestGroup
        from db.organization import UserOrganizationLink
        from django.db.models import Q
        
        query = Q()
        
        if auth_ig_codes:
            ig_ids = InterestGroup.objects.filter(code__in=auth_ig_codes).values_list('id', flat=True)
            query |= Q(entity_type=EventConnection.EntityType.COLLAB_IG, entity_id__in=ig_ids)
            
        if is_campus_lead or is_company:
            org_ids = UserOrganizationLink.objects.filter(
                user_id=user_id, verified=True
            ).values_list('org_id', flat=True)
            query |= Q(
                entity_type__in=[EventConnection.EntityType.COLLAB_CAMPUS, EventConnection.EntityType.COLLAB_COMPANY], 
                entity_id__in=org_ids
            )
            
        if has_any_campus_lead_role:
            # Scope campus-IG invites to the specific IGs the user is a campus
            # lead for (entity_id on a campus_ig invite is the InterestGroup id).
            campus_ig_codes = [
                r.replace(' CampusLead', '') for r in roles if r.endswith(' CampusLead')
            ]
            if campus_ig_codes:
                ci_ig_ids = InterestGroup.objects.filter(
                    code__in=campus_ig_codes
                ).values_list('id', flat=True)
                query |= Q(
                    entity_type=EventConnection.EntityType.COLLAB_CAMPUS_IG,
                    entity_id__in=list(ci_ig_ids),
                )

        if not query:
            return CustomResponse(
                general_message='Pending invites retrieved.',
                response=[]
            ).get_success_response()
            
        invites = EventConnection.objects.filter(
            query,
            invite_status=EventConnection.InviteStatus.PENDING,
        ).select_related('event').order_by('-created_at')
        
        invites_list = list(invites)
        ig_ids = [inv.entity_id for inv in invites_list if inv.entity_type == EventConnection.EntityType.COLLAB_IG]
        org_ids = [inv.entity_id for inv in invites_list if inv.entity_type in (EventConnection.EntityType.COLLAB_CAMPUS, EventConnection.EntityType.COLLAB_COMPANY)]
        
        from db.task import InterestGroup
        from db.organization import Organization
        igs = {str(ig.id): ig for ig in InterestGroup.objects.filter(id__in=ig_ids)}
        orgs = {str(org.id): org for org in Organization.objects.filter(id__in=org_ids)}

        serializer = MyEventInviteSerializer(
            invites_list, many=True, context={'request': request, 'igs_map': igs, 'orgs_map': orgs},
        )
        return CustomResponse(
            general_message='Pending invites retrieved.',
            response=serializer.data
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# MENTOR APPROVAL ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

def _is_company_owner_or_delegate(user_id, org_id):
    """
    Checks if a user is the owner of a company or an accepted delegate,
    given the company's organization ID.
    """
    if not org_id:
        return False
    
    from db.company import Company, CompanyAdminLink
    company = Company.objects.filter(org_id=org_id, status="verified").first()
    if not company:
        return False
    
    if company.company_user_id == user_id:
        return True
    
    return CompanyAdminLink.objects.filter(
        company=company,
        user_id=user_id,
        status='Accepted'
    ).exists()


class MentorEventApproveAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Events'])
    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        if RoleType.MENTOR.value not in roles:
            return CustomResponse(general_message='Mentor role required.').get_failure_response()

        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()

        if event.status != Event.Status.PENDING_MENTOR_APPROVAL:
            return CustomResponse(general_message='Event is not pending mentor approval.').get_failure_response()

        from db.user import MentorScopeGrant
        from api.dashboard.mentor.dash_mentor_helper import get_mentor_scopes, has_scope
        scopes = get_mentor_scopes(user_id)
        if not scopes:
            return CustomResponse(general_message='Active mentor profile not found.').get_failure_response()

        if event.organiser_type == Event.OrganiserType.CAMPUS_IG:
            if not has_scope(user_id, MentorScopeGrant.ScopeType.CAMPUS_MENTOR, event.scope_org_id):
                return CustomResponse(general_message='You are not authorized to approve this Campus IG event.').get_failure_response()
            new_status = Event.Status.PENDING_CAMPUS_APPROVAL
        elif event.organiser_type == Event.OrganiserType.GLOBAL_IG:
            if not any(st == MentorScopeGrant.ScopeType.IG_MENTOR for st, _ in scopes):
                return CustomResponse(general_message='You are not authorized to approve this Global IG event.').get_failure_response()
            from db.task import UserIgLink
            is_assigned = UserIgLink.objects.filter(
                user_id=user_id,
                ig_id=event.organiser_ig_id,
                assignment_type=UserIgLink.AssignmentType.MENTOR,
                is_active=True
            ).exists()
            if not is_assigned:
                return CustomResponse(general_message='You are not a mentor for this Interest Group.').get_failure_response()
            new_status = Event.Status.PENDING_APPROVAL
        elif event.organiser_type == Event.OrganiserType.COMPANY:
            return CustomResponse(general_message='Company events are approved by the company owner via the company approval endpoint, not here.').get_failure_response()
        else:
            return CustomResponse(general_message='Event type not supported for mentor approval.').get_failure_response()

        event.status = new_status
        event.updated_by_id = user_id
        event.save()

        log_event_action(event=event, user_id=user_id, action=EventLog.Action.APPROVED, changes={'Status': {'from': Event.Status.PENDING_MENTOR_APPROVAL, 'to': new_status}})

        from db.mentor import SystemActionLog
        SystemActionLog.objects.create(
            action_type=SystemActionLog.ActionType.IG_EVENT_APPROVE,
            actor_user_id=user_id,
            subject_user_id=event.created_by_id,
            entity_name='events',
            entity_id=event.id,
            old_data={'status': Event.Status.PENDING_MENTOR_APPROVAL},
            new_data={'status': new_status},
        )

        # Notify the event creator
        actor = User.objects.filter(id=user_id).first()
        creator = event.created_by
        if creator and actor:
            NotificationUtils.insert_notification(
                user=creator,
                title='Event Approved by Mentor',
                description=f'Your event "{event.title}" has been approved by a mentor.',
                button=None,
                url=None,
                created_by=actor,
            )

        return CustomResponse(general_message='Event approved successfully.').get_success_response()


class MentorEventRejectAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Events'])
    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        if RoleType.MENTOR.value not in roles:
            return CustomResponse(general_message='Mentor role required.').get_failure_response()

        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()

        if event.status != Event.Status.PENDING_MENTOR_APPROVAL:
            return CustomResponse(general_message='Event is not pending mentor approval.').get_failure_response()

        from db.user import MentorScopeGrant
        from api.dashboard.mentor.dash_mentor_helper import get_mentor_scopes, has_scope
        scopes = get_mentor_scopes(user_id)
        if not scopes:
            return CustomResponse(general_message='Active mentor profile not found.').get_failure_response()

        if event.organiser_type == Event.OrganiserType.CAMPUS_IG:
            if not has_scope(user_id, MentorScopeGrant.ScopeType.CAMPUS_MENTOR, event.scope_org_id):
                return CustomResponse(general_message='You are not authorized to reject this Campus IG event.').get_failure_response()
        elif event.organiser_type == Event.OrganiserType.GLOBAL_IG:
            if not any(st == MentorScopeGrant.ScopeType.IG_MENTOR for st, _ in scopes):
                return CustomResponse(general_message='You are not authorized to reject this Global IG event.').get_failure_response()
            from db.task import UserIgLink
            is_assigned = UserIgLink.objects.filter(
                user_id=user_id,
                ig_id=event.organiser_ig_id,
                assignment_type=UserIgLink.AssignmentType.MENTOR,
                is_active=True
            ).exists()
            if not is_assigned:
                return CustomResponse(general_message='You are not a mentor for this Interest Group.').get_failure_response()
        elif event.organiser_type == Event.OrganiserType.COMPANY:
            return CustomResponse(general_message='Company events are rejected by the company owner via the company approval endpoint, not here.').get_failure_response()

        reason = request.data.get('reason', '').strip()
        if not reason:
            return CustomResponse(general_message='A rejection reason is required.').get_failure_response()

        old_status = event.status
        event.status = Event.Status.REJECTED
        event.updated_by_id = user_id
        event.save()

        log_event_action(event=event, user_id=user_id, action=EventLog.Action.REJECTED, changes={'Status': {'from': old_status, 'to': Event.Status.REJECTED}}, details={'reason': reason})

        from db.mentor import SystemActionLog
        SystemActionLog.objects.create(
            action_type=SystemActionLog.ActionType.IG_EVENT_REJECT,
            actor_user_id=user_id,
            subject_user_id=event.created_by_id,
            entity_name='events',
            entity_id=event.id,
            old_data={'status': old_status},
            new_data={'status': Event.Status.REJECTED},
            remarks=reason,
        )

        # Notify the event creator
        actor = User.objects.filter(id=user_id).first()
        creator = event.created_by
        if creator and actor:
            NotificationUtils.insert_notification(
                user=creator,
                title='Event Rejected by Mentor',
                description=f'Your event "{event.title}" was rejected by a mentor. Reason: {reason}',
                button=None,
                url=None,
                created_by=actor,
            )

        return CustomResponse(general_message='Event rejected successfully.').get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# COMPANY APPROVAL ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

class CompanyEventApproveAPI(APIView):
    """
    Owner leg of the company event double-approval chain (PRD §3.1): a
    non-owner company mentor's event lands at PENDING_MENTOR_APPROVAL; the
    owner approves here, which always advances to PENDING_APPROVAL (admin
    leg) — company events never fast-path past admin, unlike campus/IG.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Events'])
    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()

        if event.organiser_type != Event.OrganiserType.COMPANY:
            return CustomResponse(general_message='This event is not a company event.').get_failure_response()

        if event.status != Event.Status.PENDING_MENTOR_APPROVAL:
            return CustomResponse(general_message='Event is not pending owner approval.').get_failure_response()

        if event.created_by_id == user_id:
            return CustomResponse(general_message='You cannot approve your own event submission.').get_failure_response(status_code=403)

        from db.company import Company
        from api.dashboard.company.company_views import is_company_owner_or_admin
        company = Company.objects.filter(org_id=event.organiser_org_id, status='verified').first()
        is_owner = is_company_owner_or_admin(user_id, company)
        if not is_owner and RoleType.ADMIN.value not in roles:
            return CustomResponse(general_message='You are not authorized to approve events for this company.').get_failure_response()

        new_status = Event.Status.PENDING_APPROVAL
        event.status = new_status
        event.updated_by_id = user_id
        event.save()

        log_event_action(event=event, user_id=user_id, action=EventLog.Action.APPROVED, changes={'Status': {'from': Event.Status.PENDING_MENTOR_APPROVAL, 'to': new_status}})

        from db.mentor import SystemActionLog
        SystemActionLog.objects.create(
            action_type=SystemActionLog.ActionType.COMPANY_EVENT_APPROVE,
            actor_user_id=user_id,
            subject_user_id=event.created_by_id,
            entity_name='events',
            entity_id=event.id,
            old_data={'status': Event.Status.PENDING_MENTOR_APPROVAL},
            new_data={'status': new_status},
        )

        actor = User.objects.filter(id=user_id).first()
        creator = event.created_by
        if creator and actor:
            NotificationUtils.insert_notification(
                user=creator,
                title='Event Approved by Company Owner',
                description=f'Your event "{event.title}" has been approved by your company owner and now awaits admin approval.',
                button=None,
                url=None,
                created_by=actor,
            )

        return CustomResponse(general_message='Event approved successfully.').get_success_response()


class CompanyEventRejectAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Events'])
    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()

        if event.organiser_type != Event.OrganiserType.COMPANY:
            return CustomResponse(general_message='This event is not a company event.').get_failure_response()

        if event.status != Event.Status.PENDING_MENTOR_APPROVAL:
            return CustomResponse(general_message='Event is not pending owner approval.').get_failure_response()

        from db.company import Company
        from api.dashboard.company.company_views import is_company_owner_or_admin
        company = Company.objects.filter(org_id=event.organiser_org_id, status='verified').first()
        is_owner = is_company_owner_or_admin(user_id, company)
        if not is_owner and RoleType.ADMIN.value not in roles:
            return CustomResponse(general_message='You are not authorized to reject events for this company.').get_failure_response()

        reason = request.data.get('reason', '').strip()
        if not reason:
            return CustomResponse(general_message='A rejection reason is required.').get_failure_response()

        old_status = event.status
        event.status = Event.Status.REJECTED
        event.updated_by_id = user_id
        event.save()

        log_event_action(event=event, user_id=user_id, action=EventLog.Action.REJECTED, changes={'Status': {'from': old_status, 'to': Event.Status.REJECTED}}, details={'reason': reason})

        from db.mentor import SystemActionLog
        SystemActionLog.objects.create(
            action_type=SystemActionLog.ActionType.COMPANY_EVENT_REJECT,
            actor_user_id=user_id,
            subject_user_id=event.created_by_id,
            entity_name='events',
            entity_id=event.id,
            old_data={'status': old_status},
            new_data={'status': Event.Status.REJECTED},
            remarks=reason,
        )

        actor = User.objects.filter(id=user_id).first()
        creator = event.created_by
        if creator and actor:
            NotificationUtils.insert_notification(
                user=creator,
                title='Event Rejected by Company Owner',
                description=f'Your event "{event.title}" was rejected by your company owner. Reason: {reason}',
                button=None,
                url=None,
                created_by=actor,
            )

        return CustomResponse(general_message='Event rejected successfully.').get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# CAMPUS APPROVAL ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

class CampusEventApproveAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Events'])
    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        
        # Must be campus lead, enabler, or higher
        if not set(roles) & {RoleType.CAMPUS_LEAD.value, RoleType.ZONAL_CAMPUS_LEAD.value, RoleType.DISTRICT_CAMPUS_LEAD.value, RoleType.ENABLER.value, RoleType.LEAD_ENABLER.value, RoleType.ADMIN.value}:
            return CustomResponse(general_message='Campus lead or enabler role required.').get_failure_response()

        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()

        if event.status != Event.Status.PENDING_CAMPUS_APPROVAL:
            return CustomResponse(general_message='Event is not pending campus approval.').get_failure_response()

        # Verify campus lead matches the campus of the event (event.scope_org_id)
        if RoleType.ADMIN.value not in roles:
            if not _is_active_campus_member(user_id, event.scope_org_id):
                return CustomResponse(general_message='You are not authorized to approve events for this campus.').get_failure_response()

        # A campus is the final authority on its own events at any scope, so
        # campus approval publishes them outright with no admin step. Campus
        # IG events still continue to the next approval stage.
        if event.organiser_type == Event.OrganiserType.CAMPUS:
            new_status = resolve_terminal_status(event, Event.Status.PUBLISHED)
        else:
            new_status = Event.Status.PENDING_APPROVAL

        event.status = new_status
        event.updated_by_id = user_id
        event.save()

        log_event_action(event=event, user_id=user_id, action=EventLog.Action.APPROVED, changes={'Status': {'from': Event.Status.PENDING_CAMPUS_APPROVAL, 'to': new_status}})

        from db.mentor import SystemActionLog
        SystemActionLog.objects.create(
            action_type=SystemActionLog.ActionType.CAMPUS_EVENT_APPROVE,
            actor_user_id=user_id,
            subject_user_id=event.created_by_id,
            entity_name='events',
            entity_id=event.id,
            old_data={'status': Event.Status.PENDING_CAMPUS_APPROVAL},
            new_data={'status': new_status},
        )

        # Notify the event creator
        actor = User.objects.filter(id=user_id).first()
        creator = event.created_by
        if creator and actor:
            if new_status == Event.Status.COMPLETED:
                NotificationUtils.insert_notification(
                    user=creator,
                    title='Event Recorded',
                    description=f'Your past event "{event.title}" was approved by the campus and is now on record.',
                    button='View',
                    url=f'/events/{event.id}/',
                    created_by=actor,
                )
            elif new_status in (Event.Status.PUBLISHED, Event.Status.ONGOING):
                NotificationUtils.insert_notification(
                    user=creator,
                    title='Event Published',
                    description=f'Your event "{event.title}" was approved by the campus and is now live!',
                    button='View',
                    url=f'/events/{event.id}/',
                    created_by=actor,
                )
            else:
                NotificationUtils.insert_notification(
                    user=creator,
                    title='Event Approved by Campus',
                    description=f'Your event "{event.title}" has been approved by the campus lead.',
                    button=None,
                    url=None,
                    created_by=actor,
                )

        # Announce only events an audience can still attend
        if should_announce(new_status) and actor:
            BroadcastUtils.create_broadcast(
                title='New Event Published',
                description=f'A new Campus event "{event.title}" is now live!',
                target_type='campus',
                target_id=event.scope_org_id,
                created_by=actor,
                expiry_key='event_published',
                url=f'/events/{event.id}/',
            )

        return CustomResponse(general_message='Event approved successfully.').get_success_response()


class CampusEventRejectAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Events'])
    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        
        if not set(roles) & {RoleType.CAMPUS_LEAD.value, RoleType.ZONAL_CAMPUS_LEAD.value, RoleType.DISTRICT_CAMPUS_LEAD.value, RoleType.ENABLER.value, RoleType.LEAD_ENABLER.value, RoleType.ADMIN.value}:
            return CustomResponse(general_message='Campus lead or enabler role required.').get_failure_response()

        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()

        if event.status != Event.Status.PENDING_CAMPUS_APPROVAL:
            return CustomResponse(general_message='Event is not pending campus approval.').get_failure_response()

        # Verify campus lead matches the campus of the event (event.scope_org_id)
        if RoleType.ADMIN.value not in roles:
            if not _is_active_campus_member(user_id, event.scope_org_id):
                return CustomResponse(general_message='You are not authorized to reject events for this campus.').get_failure_response()

        reason = request.data.get('reason', '').strip()
        if not reason:
            return CustomResponse(general_message='A rejection reason is required.').get_failure_response()

        old_status = event.status
        event.status = Event.Status.REJECTED
        event.updated_by_id = user_id
        event.save()

        log_event_action(event=event, user_id=user_id, action=EventLog.Action.REJECTED, changes={'Status': {'from': old_status, 'to': Event.Status.REJECTED}}, details={'reason': reason})

        from db.mentor import SystemActionLog
        SystemActionLog.objects.create(
            action_type=SystemActionLog.ActionType.CAMPUS_EVENT_REJECT,
            actor_user_id=user_id,
            subject_user_id=event.created_by_id,
            entity_name='events',
            entity_id=event.id,
            old_data={'status': old_status},
            new_data={'status': Event.Status.REJECTED},
            remarks=reason,
        )

        # Notify the event creator
        actor = User.objects.filter(id=user_id).first()
        creator = event.created_by
        if creator and actor:
            NotificationUtils.insert_notification(
                user=creator,
                title='Event Rejected by Campus',
                description=f'Your event "{event.title}" was rejected by the campus lead. Reason: {reason}',
                button=None,
                url=None,
                created_by=actor,
            )

        return CustomResponse(general_message='Event rejected successfully.').get_success_response()
