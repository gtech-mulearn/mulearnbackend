"""
Manage Events API views.
Organiser / co-owner access required for all endpoints.
"""
import uuid
from django.utils import timezone
from django.db import transaction
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from db.events import Event, EventConnection, EventLog
from db.user import User
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils
from utils.types import RoleType

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
from .event_image_utils import delete_stale_event_media, merge_event_write_payload
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
    """Returns a list of Organization IDs for companies where the user is a creator or mentor."""
    company_org_ids = set()
    
    if RoleType.COMPANY.value in roles:
        from db.company import Company
        from db.organization import Organization
        from utils.types import OrganizationType
        company = Company.objects.filter(company_user_id=user_id, status="verified").first()
        if company:
            org = Organization.objects.filter(title=company.name, org_type=OrganizationType.COMPANY.value).first()
            if org:
                company_org_ids.add(org.id)
                
    if RoleType.MENTOR.value in roles:
        from db.user import UserMentor
        mentors = UserMentor.objects.filter(
            user_id=user_id, 
            mentor_tier=UserMentor.MentorTier.COMPANY_MENTOR, 
            status=UserMentor.Status.APPROVED
        )
        for mentor in mentors:
            if mentor.org_id:
                company_org_ids.add(mentor.org_id)
                
    return list(company_org_ids)


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

            from django.db.models import Q
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
                    from db.user import UserMentor
                    mentor = UserMentor.objects.filter(user_id=user_id, status=UserMentor.Status.APPROVED).first()
                    if mentor:
                        if mentor.mentor_tier == UserMentor.MentorTier.CAMPUS_MENTOR:
                            events = _get_manageable_events().filter(
                                status=status,
                                organiser_type=Event.OrganiserType.CAMPUS_IG,
                                scope_org_id=mentor.org_id
                            )
                        elif mentor.mentor_tier == UserMentor.MentorTier.IG_MENTOR:
                            from db.task import UserIgLink
                            user_ig_ids = UserIgLink.objects.filter(
                                user_id=user_id,
                                assignment_type=UserIgLink.AssignmentType.MENTOR,
                                is_active=True
                            ).values_list('ig_id', flat=True)
                            events = _get_manageable_events().filter(
                                status=status,
                                organiser_type=Event.OrganiserType.GLOBAL_IG,
                                organiser_ig_id__in=user_ig_ids
                            )
                        else:
                            events = _get_manageable_events().none()
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
            sort_fields={'created_at': '-created_at', 'start_datetime': 'start_datetime'},
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
            # User is ONLY a mentor
            from db.user import UserMentor
            mentor = UserMentor.objects.filter(user_id=user_id, status=UserMentor.Status.APPROVED).first()
            if not mentor:
                return CustomResponse(general_message='Active mentor profile not found.').get_failure_response()
            
            payload_organiser_type = request.data.get('organiser_type')
            
            if mentor.mentor_tier == UserMentor.MentorTier.CAMPUS_MENTOR:
                if payload_organiser_type != Event.OrganiserType.CAMPUS_IG.value:
                    return CustomResponse(general_message='Campus Mentors can only create Campus IG events.').get_failure_response()
            elif mentor.mentor_tier == UserMentor.MentorTier.COMPANY_MENTOR:
                if payload_organiser_type != Event.OrganiserType.COMPANY.value:
                    return CustomResponse(general_message='Company Mentors can only create Company events.').get_failure_response()
            elif mentor.mentor_tier == UserMentor.MentorTier.IG_MENTOR:
                if payload_organiser_type != Event.OrganiserType.GLOBAL_IG.value:
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

        payload, merge_error = merge_event_write_payload(
            request, partial=False, event=None,
        )
        if merge_error:
            return CustomResponse(general_message=merge_error).get_failure_response()

        serializer = EventWriteSerializer(
            data=payload,
            context={'user_id': user_id},
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors,
            ).get_failure_response()

        event = serializer.save()

        return CustomResponse(
            general_message='Event created successfully.',
            response=EventDetailSerializer(
                event, context={'user_id': user_id, 'request': request},
            ).data,
        ).get_success_response()


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

        if event.status in (Event.Status.CANCELLED, Event.Status.COMPLETED):
            return CustomResponse(
                general_message=f'Cannot edit a {event.status} event.'
            ).get_failure_response()

        old_cover = event.cover_image
        old_banner = event.banner_image

        payload, merge_error = merge_event_write_payload(
            request, partial=partial, event=event,
        )
        if merge_error:
            return CustomResponse(general_message=merge_error).get_failure_response()

        # Enforce Mentor Update Scopes
        roles = JWTUtils.fetch_role(request)
        if RoleType.MENTOR.value in roles and not (set(roles) & MANAGEABLE_ROLES - {RoleType.MENTOR.value}):
            # User is ONLY a mentor
            from db.user import UserMentor
            mentor = UserMentor.objects.filter(user_id=user_id, status=UserMentor.Status.APPROVED).first()
            if not mentor:
                return CustomResponse(general_message='Active mentor profile not found.').get_failure_response()
                
            payload_organiser_type = payload.get('organiser_type', event.organiser_type)
            
            if mentor.mentor_tier == UserMentor.MentorTier.CAMPUS_MENTOR:
                if payload_organiser_type != Event.OrganiserType.CAMPUS_IG.value:
                    return CustomResponse(general_message='Campus Mentors can only manage Campus IG events.').get_failure_response()
            elif mentor.mentor_tier == UserMentor.MentorTier.COMPANY_MENTOR:
                if payload_organiser_type != Event.OrganiserType.COMPANY.value:
                    return CustomResponse(general_message='Company Mentors can only manage Company events.').get_failure_response()
            elif mentor.mentor_tier == UserMentor.MentorTier.IG_MENTOR:
                if payload_organiser_type != Event.OrganiserType.GLOBAL_IG.value:
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

        serializer = EventWriteSerializer(
            event, data=payload,
            partial=partial,
            context={'user_id': user_id},
        )
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        serializer.save()
        delete_stale_event_media(old_cover, event.cover_image)
        delete_stale_event_media(old_banner, event.banner_image)

        return CustomResponse(
            general_message='Event updated successfully.',
            response=EventDetailSerializer(
                event, context={'user_id': user_id, 'request': request},
            ).data,
        ).get_success_response()

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

        # Must be in the future
        if event.start_datetime and event.start_datetime <= timezone.now():
            return CustomResponse(
                general_message='Cannot publish: start_datetime must be in the future.'
            ).get_failure_response()

        # Determine next status based on organiser type
        if RoleType.ADMIN.value in roles:
            new_status = Event.Status.PUBLISHED
        elif event.organiser_type == Event.OrganiserType.CAMPUS_IG:
            # Check if creator is an approved CAMPUS_MENTOR for this campus
            from db.user import UserMentor
            is_campus_mentor = UserMentor.objects.filter(
                user_id=user_id,
                mentor_tier=UserMentor.MentorTier.CAMPUS_MENTOR,
                org_id=event.scope_org_id,
                status=UserMentor.Status.APPROVED
            ).exists()
            if is_campus_mentor:
                new_status = Event.Status.PENDING_CAMPUS_APPROVAL
            else:
                new_status = Event.Status.PENDING_MENTOR_APPROVAL
        elif event.organiser_type == Event.OrganiserType.GLOBAL_IG:
            # Check if creator is an approved IG_MENTOR for this IG
            from db.user import UserMentor
            from db.task import UserIgLink
            is_mentor = UserMentor.objects.filter(
                user_id=user_id,
                mentor_tier=UserMentor.MentorTier.IG_MENTOR,
                status=UserMentor.Status.APPROVED
            ).exists()
            is_assigned = UserIgLink.objects.filter(
                user_id=user_id,
                ig_id=event.organiser_ig_id,
                assignment_type=UserIgLink.AssignmentType.MENTOR,
                is_active=True
            ).exists()
            if is_mentor and is_assigned:
                new_status = Event.Status.PENDING_APPROVAL
            else:
                new_status = Event.Status.PENDING_MENTOR_APPROVAL
        elif event.organiser_type == Event.OrganiserType.CAMPUS:
            if RoleType.CAMPUS_LEAD.value in roles:
                new_status = Event.Status.PENDING_APPROVAL
            else:
                new_status = Event.Status.PENDING_CAMPUS_APPROVAL
        else:
            new_status = Event.Status.PENDING_APPROVAL

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
    elif conn.entity_type in (
        EventConnection.EntityType.COLLAB_CAMPUS,
        EventConnection.EntityType.COLLAB_COMPANY,
    ):
        in_org = UserOrganizationLink.objects.filter(
            user_id=user_id, org_id=conn.entity_id, verified=True
        ).exists()
        return in_org and (
            RoleType.CAMPUS_LEAD.value in roles or RoleType.COMPANY.value in roles
        )
    elif conn.entity_type == EventConnection.EntityType.COLLAB_CAMPUS_IG:
        return any(r.endswith(' CampusLead') for r in roles)
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
            query |= Q(entity_type=EventConnection.EntityType.COLLAB_CAMPUS_IG)
            
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

        from db.user import UserMentor
        mentor = UserMentor.objects.filter(user_id=user_id, status=UserMentor.Status.APPROVED).first()
        if not mentor:
            return CustomResponse(general_message='Active mentor profile not found.').get_failure_response()

        if event.organiser_type == Event.OrganiserType.CAMPUS_IG:
            if mentor.mentor_tier != UserMentor.MentorTier.CAMPUS_MENTOR or str(mentor.org_id) != str(event.scope_org_id):
                return CustomResponse(general_message='You are not authorized to approve this Campus IG event.').get_failure_response()
            new_status = Event.Status.PENDING_CAMPUS_APPROVAL
        elif event.organiser_type == Event.OrganiserType.GLOBAL_IG:
            if mentor.mentor_tier != UserMentor.MentorTier.IG_MENTOR:
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
        else:
            return CustomResponse(general_message='Event type not supported for mentor approval.').get_failure_response()

        event.status = new_status
        event.updated_by_id = user_id
        event.save()

        log_event_action(event=event, user_id=user_id, action=EventLog.Action.APPROVED, changes={'Status': {'from': Event.Status.PENDING_MENTOR_APPROVAL, 'to': new_status}})
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

        from db.user import UserMentor
        mentor = UserMentor.objects.filter(user_id=user_id, status=UserMentor.Status.APPROVED).first()
        if not mentor:
            return CustomResponse(general_message='Active mentor profile not found.').get_failure_response()

        if event.organiser_type == Event.OrganiserType.CAMPUS_IG:
            if mentor.mentor_tier != UserMentor.MentorTier.CAMPUS_MENTOR or str(mentor.org_id) != str(event.scope_org_id):
                return CustomResponse(general_message='You are not authorized to reject this Campus IG event.').get_failure_response()
        elif event.organiser_type == Event.OrganiserType.GLOBAL_IG:
            if mentor.mentor_tier != UserMentor.MentorTier.IG_MENTOR:
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

        reason = request.data.get('reason', '').strip()
        if not reason:
            return CustomResponse(general_message='A rejection reason is required.').get_failure_response()

        old_status = event.status
        event.status = Event.Status.REJECTED
        event.updated_by_id = user_id
        event.save()

        log_event_action(event=event, user_id=user_id, action=EventLog.Action.REJECTED, changes={'Status': {'from': old_status, 'to': Event.Status.REJECTED}}, details={'reason': reason})
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
        
        # Must be campus lead or higher
        if not set(roles) & {RoleType.CAMPUS_LEAD.value, RoleType.ZONAL_CAMPUS_LEAD.value, RoleType.DISTRICT_CAMPUS_LEAD.value, RoleType.ADMIN.value}:
            return CustomResponse(general_message='Campus lead role required.').get_failure_response()

        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()

        if event.status != Event.Status.PENDING_CAMPUS_APPROVAL:
            return CustomResponse(general_message='Event is not pending campus approval.').get_failure_response()

        # Verify campus lead matches the campus of the event (event.scope_org_id)
        if RoleType.ADMIN.value not in roles:
            from db.organization import UserOrganizationLink
            is_member = UserOrganizationLink.objects.filter(
                user_id=user_id,
                org_id=event.scope_org_id
            ).exists()
            if not is_member:
                return CustomResponse(general_message='You are not authorized to approve events for this campus.').get_failure_response()
        
        event.status = Event.Status.PENDING_APPROVAL
        event.updated_by_id = user_id
        event.save()

        log_event_action(event=event, user_id=user_id, action=EventLog.Action.APPROVED, changes={'Status': {'from': Event.Status.PENDING_CAMPUS_APPROVAL, 'to': Event.Status.PENDING_APPROVAL}})
        return CustomResponse(general_message='Event approved successfully.').get_success_response()


class CampusEventRejectAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Events'])
    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        
        if not set(roles) & {RoleType.CAMPUS_LEAD.value, RoleType.ZONAL_CAMPUS_LEAD.value, RoleType.DISTRICT_CAMPUS_LEAD.value, RoleType.ADMIN.value}:
            return CustomResponse(general_message='Campus lead role required.').get_failure_response()

        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(general_message='Event not found.').get_failure_response()

        if event.status != Event.Status.PENDING_CAMPUS_APPROVAL:
            return CustomResponse(general_message='Event is not pending campus approval.').get_failure_response()

        # Verify campus lead matches the campus of the event (event.scope_org_id)
        if RoleType.ADMIN.value not in roles:
            from db.organization import UserOrganizationLink
            is_member = UserOrganizationLink.objects.filter(
                user_id=user_id,
                org_id=event.scope_org_id
            ).exists()
            if not is_member:
                return CustomResponse(general_message='You are not authorized to reject events for this campus.').get_failure_response()

        reason = request.data.get('reason', '').strip()
        if not reason:
            return CustomResponse(general_message='A rejection reason is required.').get_failure_response()

        old_status = event.status
        event.status = Event.Status.REJECTED
        event.updated_by_id = user_id
        event.save()

        log_event_action(event=event, user_id=user_id, action=EventLog.Action.REJECTED, changes={'Status': {'from': old_status, 'to': Event.Status.REJECTED}}, details={'reason': reason})
        return CustomResponse(general_message='Event rejected successfully.').get_success_response()
