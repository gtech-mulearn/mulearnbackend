"""
Manage event endpoints — CRUD, publish, co-owners, collaborators.

Requires JWT auth. Most actions need owner or co-owner authority.
"""

import uuid

from rest_framework.views import APIView

from db.event import (
    Event, EventCoOwner, EventCollaborator, EventInterest,
)
from db.user import User
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils, DateTimeUtils
from .permissions import is_event_owner_or_coowner, is_admin
from .serializers import (
    CoOwnerAddSerializer, CollaboratorInviteSerializer,
    EventCoOwnerReadSerializer, EventCollaboratorReadSerializer,
    EventDetailSerializer, EventListSerializer, EventWriteSerializer,
)


class ManageEventListCreateAPI(APIView):
    """
    GET  manage/events/  — events the user owns or co-owns.
    POST manage/events/  — create a new event.
    """

    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        # Events the user created or co-owns
        owned_ids = list(
            Event.objects.filter(
                created_by_id=user_id, deleted_at__isnull=True
            ).values_list("id", flat=True)
        )
        co_owned_ids = list(
            EventCoOwner.objects.filter(user_id=user_id)
            .values_list("event_id", flat=True)
        )
        all_ids = list(set(owned_ids + co_owned_ids))

        events = Event.objects.filter(
            id__in=all_ids, deleted_at__isnull=True
        ).order_by("-created_at")

        paginated = CommonUtils.get_paginated_queryset(
            events, request, search_fields=["title"]
        )

        serializer = EventListSerializer(paginated.get("queryset"), many=True)

        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated.get("pagination"),
        )

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        serializer = EventWriteSerializer(
            data=request.data,
            context={"user_id": user_id},
        )

        if serializer.is_valid():
            event = serializer.save()
            detail = EventDetailSerializer(event, context={"user_id": user_id})
            return CustomResponse(
                general_message="Event created successfully",
                response=detail.data,
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors
        ).get_failure_response()


class ManageEventDetailAPI(APIView):
    """
    GET    manage/events/:id/  — manage view + audit log.
    PUT    manage/events/:id/  — full event update.
    PATCH  manage/events/:id/  — partial event update.
    DELETE manage/events/:id/  — cancel event (soft delete).
    """

    authentication_classes = [CustomizePermission]

    def get(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        event = Event.objects.filter(id=event_id, deleted_at__isnull=True).first()

        if not event:
            return CustomResponse(
                general_message="Event not found"
            ).get_failure_response()

        if not is_event_owner_or_coowner(user_id, event) and not is_admin(user_id):
            return CustomResponse(
                general_message="You do not have permission to manage this event"
            ).get_failure_response()

        serializer = EventDetailSerializer(event, context={"user_id": user_id})
        return CustomResponse(response=serializer.data).get_success_response()

    def put(self, request, event_id):
        return self._update(request, event_id, partial=False)

    def patch(self, request, event_id):
        return self._update(request, event_id, partial=True)

    def delete(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        event = Event.objects.filter(id=event_id, deleted_at__isnull=True).first()

        if not event:
            return CustomResponse(
                general_message="Event not found"
            ).get_failure_response()

        if not is_event_owner_or_coowner(user_id, event) and not is_admin(user_id):
            return CustomResponse(
                general_message="You do not have permission to cancel this event"
            ).get_failure_response()

        now = DateTimeUtils.get_current_utc_time()
        event.status = Event.Status.CANCELLED
        event.deleted_at = now
        event.deleted_by_id = user_id
        event.updated_by_id = user_id
        event.updated_at = now
        event.save()

        return CustomResponse(
            general_message=f"Event '{event.title}' has been cancelled"
        ).get_success_response()

    def _update(self, request, event_id, partial):
        user_id = JWTUtils.fetch_user_id(request)
        event = Event.objects.filter(id=event_id, deleted_at__isnull=True).first()

        if not event:
            return CustomResponse(
                general_message="Event not found"
            ).get_failure_response()

        if not is_event_owner_or_coowner(user_id, event) and not is_admin(user_id):
            return CustomResponse(
                general_message="You do not have permission to edit this event"
            ).get_failure_response()

        serializer = EventWriteSerializer(
            instance=event,
            data=request.data,
            partial=partial,
            context={"user_id": user_id},
        )

        if serializer.is_valid():
            event = serializer.save()
            detail = EventDetailSerializer(event, context={"user_id": user_id})
            return CustomResponse(
                general_message="Event updated successfully",
                response=detail.data,
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors
        ).get_failure_response()


class ManageEventPublishAPI(APIView):
    """POST manage/events/:id/publish/ — publish from draft or re-submit after rejection."""

    authentication_classes = [CustomizePermission]

    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        event = Event.objects.filter(id=event_id, deleted_at__isnull=True).first()

        if not event:
            return CustomResponse(
                general_message="Event not found"
            ).get_failure_response()

        if not is_event_owner_or_coowner(user_id, event) and not is_admin(user_id):
            return CustomResponse(
                general_message="You do not have permission to publish this event"
            ).get_failure_response()

        if event.status not in (Event.Status.DRAFT,):
            return CustomResponse(
                general_message=f"Cannot publish event with status '{event.status}'"
            ).get_failure_response()

        # Determine the target status based on approval flow
        from .permissions import determine_initial_status
        from db.event import EventOrganiser

        organiser = EventOrganiser.objects.filter(event=event).first()
        if organiser:
            new_status = determine_initial_status(
                organiser.organiser_type,
                user_id,
                organiser.ci_org_id_id or organiser.org_id_id,
            )
        else:
            new_status = Event.Status.PUBLISHED

        # If the status would be draft (admin/campus/company), go straight to published
        if new_status == Event.Status.DRAFT:
            new_status = Event.Status.PUBLISHED

        now = DateTimeUtils.get_current_utc_time()
        event.status = new_status
        event.updated_by_id = user_id
        event.updated_at = now
        event.save()

        return CustomResponse(
            general_message=f"Event submitted successfully (status: {new_status})"
        ).get_success_response()


# ──────────────────────────────────────────────────
# Co-Owners
# ──────────────────────────────────────────────────

class ManageEventCoOwnerAPI(APIView):
    """
    GET  manage/events/:id/co-owners/  — list co-owners.
    POST manage/events/:id/co-owners/  — add co-owners.
    """

    authentication_classes = [CustomizePermission]

    def get(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        event = Event.objects.filter(id=event_id, deleted_at__isnull=True).first()

        if not event:
            return CustomResponse(general_message="Event not found").get_failure_response()

        if not is_event_owner_or_coowner(user_id, event) and not is_admin(user_id):
            return CustomResponse(
                general_message="Permission denied"
            ).get_failure_response()

        co_owners = EventCoOwner.objects.filter(event=event).select_related("user")
        serializer = EventCoOwnerReadSerializer(co_owners, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        event = Event.objects.filter(id=event_id, deleted_at__isnull=True).first()

        if not event:
            return CustomResponse(general_message="Event not found").get_failure_response()

        if not is_event_owner_or_coowner(user_id, event) and not is_admin(user_id):
            return CustomResponse(
                general_message="Permission denied"
            ).get_failure_response()

        serializer = CoOwnerAddSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        target_user_id = serializer.validated_data["user_id"]
        role = serializer.validated_data.get("role", EventCoOwner.CoOwnerRole.CO_OWNER)

        if not User.objects.filter(id=target_user_id).exists():
            return CustomResponse(general_message="User not found").get_failure_response()

        if EventCoOwner.objects.filter(event=event, user_id=target_user_id).exists():
            return CustomResponse(
                general_message="User is already a co-owner of this event"
            ).get_failure_response()

        EventCoOwner.objects.create(
            id=str(uuid.uuid4()),
            event=event,
            user_id=target_user_id,
            role=role,
            added_by_id=user_id,
            added_at=DateTimeUtils.get_current_utc_time(),
        )

        return CustomResponse(
            general_message="Co-owner added successfully"
        ).get_success_response()


class ManageEventCoOwnerRemoveAPI(APIView):
    """DELETE manage/events/:id/co-owners/:coid/ — remove a co-owner."""

    authentication_classes = [CustomizePermission]

    def delete(self, request, event_id, co_owner_id):
        user_id = JWTUtils.fetch_user_id(request)
        event = Event.objects.filter(id=event_id, deleted_at__isnull=True).first()

        if not event:
            return CustomResponse(general_message="Event not found").get_failure_response()

        if not is_event_owner_or_coowner(user_id, event) and not is_admin(user_id):
            return CustomResponse(general_message="Permission denied").get_failure_response()

        co_owner = EventCoOwner.objects.filter(id=co_owner_id, event=event).first()
        if not co_owner:
            return CustomResponse(general_message="Co-owner not found").get_failure_response()

        co_owner.delete()
        return CustomResponse(
            general_message="Co-owner removed successfully"
        ).get_success_response()


# ──────────────────────────────────────────────────
# Collaborators
# ──────────────────────────────────────────────────

class ManageEventCollaboratorAPI(APIView):
    """
    GET  manage/events/:id/collaborators/  — list all invite statuses.
    POST manage/events/:id/collaborators/  — invite collaborators.
    """

    authentication_classes = [CustomizePermission]

    def get(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        event = Event.objects.filter(id=event_id, deleted_at__isnull=True).first()

        if not event:
            return CustomResponse(general_message="Event not found").get_failure_response()

        if not is_event_owner_or_coowner(user_id, event) and not is_admin(user_id):
            return CustomResponse(general_message="Permission denied").get_failure_response()

        collaborators = EventCollaborator.objects.filter(event=event).select_related(
            "ig_id", "org_id", "ci_org_id", "ci_ig_id"
        )
        serializer = EventCollaboratorReadSerializer(collaborators, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        event = Event.objects.filter(id=event_id, deleted_at__isnull=True).first()

        if not event:
            return CustomResponse(general_message="Event not found").get_failure_response()

        if not is_event_owner_or_coowner(user_id, event) and not is_admin(user_id):
            return CustomResponse(general_message="Permission denied").get_failure_response()

        serializer = CollaboratorInviteSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        data = serializer.validated_data
        now = DateTimeUtils.get_current_utc_time()

        collaborator = EventCollaborator.objects.create(
            id=str(uuid.uuid4()),
            event=event,
            collaborator_type=data["collaborator_type"],
            ig_id_id=data.get("ig_id"),
            org_id_id=data.get("org_id"),
            ci_org_id_id=data.get("ci_org_id"),
            ci_ig_id_id=data.get("ci_ig_id"),
            role_label=data.get("role_label"),
            invite_status=EventCollaborator.InviteStatus.PENDING,
            invited_at=now,
            created_by_id=user_id,
            created_at=now,
        )

        # Mark event as collaboration if not already
        if not event.is_collaboration:
            event.is_collaboration = True
            event.save(update_fields=["is_collaboration"])

        return CustomResponse(
            general_message="Collaborator invite sent",
            response={"collaborator_id": collaborator.id},
        ).get_success_response()


class ManageEventCollaboratorRemoveAPI(APIView):
    """DELETE manage/events/:id/collaborators/:cid/ — remove a collaborator."""

    authentication_classes = [CustomizePermission]

    def delete(self, request, event_id, collaborator_id):
        user_id = JWTUtils.fetch_user_id(request)
        event = Event.objects.filter(id=event_id, deleted_at__isnull=True).first()

        if not event:
            return CustomResponse(general_message="Event not found").get_failure_response()

        if not is_event_owner_or_coowner(user_id, event) and not is_admin(user_id):
            return CustomResponse(general_message="Permission denied").get_failure_response()

        collab = EventCollaborator.objects.filter(id=collaborator_id, event=event).first()
        if not collab:
            return CustomResponse(general_message="Collaborator not found").get_failure_response()

        collab.delete()
        return CustomResponse(
            general_message="Collaborator removed successfully"
        ).get_success_response()


class ManageEventCollaboratorAcceptAPI(APIView):
    """POST manage/events/:id/collaborators/:cid/accept/ — accept an invite."""

    authentication_classes = [CustomizePermission]

    def post(self, request, event_id, collaborator_id):
        user_id = JWTUtils.fetch_user_id(request)

        collab = EventCollaborator.objects.filter(
            id=collaborator_id, event_id=event_id,
            invite_status=EventCollaborator.InviteStatus.PENDING,
        ).first()
        if not collab:
            return CustomResponse(
                general_message="Collaboration invite not found or already responded"
            ).get_failure_response()

        # Verify the user is the lead of the invited entity
        from .permissions import is_ig_lead_of, is_campus_lead_of, is_campus_ig_lead_of
        authorized = False
        if collab.collaborator_type == 'ig' and collab.ig_id_id:
            authorized = is_ig_lead_of(user_id, collab.ig_id_id)
        elif collab.collaborator_type == 'campus' and collab.org_id_id:
            authorized = is_campus_lead_of(user_id, collab.org_id_id)
        elif collab.collaborator_type == 'campus_ig' and collab.ci_org_id_id and collab.ci_ig_id_id:
            authorized = is_campus_ig_lead_of(user_id, collab.ci_org_id_id, collab.ci_ig_id_id)
        elif collab.collaborator_type == 'company' and collab.org_id_id:
            # Company rep — check org membership
            from db.organization import UserOrganizationLink
            authorized = UserOrganizationLink.objects.filter(
                user_id=user_id, org_id=collab.org_id_id
            ).exists()

        if not authorized and not is_admin(user_id):
            return CustomResponse(
                general_message="You are not authorized to accept this invite"
            ).get_failure_response()

        now = DateTimeUtils.get_current_utc_time()
        collab.invite_status = EventCollaborator.InviteStatus.ACCEPTED
        collab.responded_at = now
        collab.save()

        return CustomResponse(
            general_message="Collaboration accepted"
        ).get_success_response()


class ManageEventCollaboratorRejectAPI(APIView):
    """POST manage/events/:id/collaborators/:cid/reject/ — reject an invite."""

    authentication_classes = [CustomizePermission]

    def post(self, request, event_id, collaborator_id):
        user_id = JWTUtils.fetch_user_id(request)

        collab = EventCollaborator.objects.filter(
            id=collaborator_id, event_id=event_id,
            invite_status=EventCollaborator.InviteStatus.PENDING,
        ).first()
        if not collab:
            return CustomResponse(
                general_message="Collaboration invite not found or already responded"
            ).get_failure_response()

        # Same authorization as accept
        from .permissions import is_ig_lead_of, is_campus_lead_of, is_campus_ig_lead_of
        authorized = False
        if collab.collaborator_type == 'ig' and collab.ig_id_id:
            authorized = is_ig_lead_of(user_id, collab.ig_id_id)
        elif collab.collaborator_type == 'campus' and collab.org_id_id:
            authorized = is_campus_lead_of(user_id, collab.org_id_id)
        elif collab.collaborator_type == 'campus_ig' and collab.ci_org_id_id and collab.ci_ig_id_id:
            authorized = is_campus_ig_lead_of(user_id, collab.ci_org_id_id, collab.ci_ig_id_id)
        elif collab.collaborator_type == 'company' and collab.org_id_id:
            from db.organization import UserOrganizationLink
            authorized = UserOrganizationLink.objects.filter(
                user_id=user_id, org_id=collab.org_id_id
            ).exists()

        if not authorized and not is_admin(user_id):
            return CustomResponse(
                general_message="You are not authorized to reject this invite"
            ).get_failure_response()

        now = DateTimeUtils.get_current_utc_time()
        collab.invite_status = EventCollaborator.InviteStatus.REJECTED
        collab.rejection_reason = request.data.get("reason", "")
        collab.responded_at = now
        collab.save()

        return CustomResponse(
            general_message="Collaboration rejected"
        ).get_success_response()
