"""
Public event endpoints — no management authority required.

GET  events/               — Viewer-scoped event feed
GET  events/featured/      — Homepage slider (public)
GET  events/:id/           — Event detail page
POST events/:id/interest/  — Click "I'm Going"
DEL  events/:id/interest/  — Remove "I'm Going"
"""

import uuid

from django.db.models import Q
from rest_framework.views import APIView

from db.event import (
    Event, EventCollaborator, EventInterest, EventOrganiser, EventScope,
)
from db.task import InterestGroup
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils, DateTimeUtils
from .serializers import EventDetailSerializer, EventListSerializer


class EventListAPI(APIView):
    """
    GET events/ — paginated event feed (published, upcoming/ongoing).

    Query params:
        event_type  — filter by event type enum
        cluster     — filter by IG cluster (coder, maker, manager, creative)
        ig          — filter by Interest Group ID
        campus      — filter by campus (organization) ID
        company     — filter by company (organization) ID
    Each entity filter includes events where the entity is the organiser,
    the scope target, OR an accepted collaborator.
    """

    authentication_classes = [CustomizePermission]

    def get(self, request):
        base_qs = (
            Event.objects
            .filter(
                status__in=[Event.Status.PUBLISHED, Event.Status.ONGOING],
                deleted_at__isnull=True,
            )
        )

        # ── Event type filter ─────────────────────────────
        event_type = request.query_params.get("event_type")
        if event_type:
            base_qs = base_qs.filter(event_type=event_type)

        # ── Entity filters ────────────────────────────────
        # Each collects matching event IDs from organiser + scope + collaborator,
        # then intersects with the base queryset.

        ig_id = request.query_params.get("ig")
        campus_id = request.query_params.get("campus")
        company_id = request.query_params.get("company")
        cluster = request.query_params.get("cluster")

        entity_event_ids = None  # None = no entity filter applied

        if ig_id:
            entity_event_ids = self._events_for_ig(ig_id)

        elif campus_id:
            entity_event_ids = self._events_for_campus(campus_id)

        elif company_id:
            entity_event_ids = self._events_for_company(company_id)

        elif cluster:
            entity_event_ids = self._events_for_cluster(cluster)

        if entity_event_ids is not None:
            base_qs = base_qs.filter(id__in=entity_event_ids)

        events = base_qs.order_by("-start_datetime")

        paginated = CommonUtils.get_paginated_queryset(
            events, request, search_fields=["title", "description"]
        )

        serializer = EventListSerializer(paginated.get("queryset"), many=True)

        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated.get("pagination"),
        )

    # ── Entity filter helpers ─────────────────────────────

    @staticmethod
    def _events_for_ig(ig_id):
        """Events organised by, scoped to, or collaborated with a specific IG."""
        organised = EventOrganiser.objects.filter(
            Q(organiser_type="global_ig", ig_id_id=ig_id) |
            Q(organiser_type="campus_ig", ci_ig_id_id=ig_id)
        ).values_list("event_id", flat=True)

        scoped = EventScope.objects.filter(
            Q(scope="ig", target_ig_id_id=ig_id) |
            Q(scope="campus_ig", target_ci_ig_id_id=ig_id)
        ).values_list("event_id", flat=True)

        collaborated = EventCollaborator.objects.filter(
            Q(collaborator_type="ig", ig_id_id=ig_id) |
            Q(collaborator_type="campus_ig", ci_ig_id_id=ig_id),
            invite_status="accepted",
        ).values_list("event_id", flat=True)

        return set(organised) | set(scoped) | set(collaborated)

    @staticmethod
    def _events_for_campus(campus_id):
        """Events organised by, scoped to, or collaborated with a campus."""
        organised = EventOrganiser.objects.filter(
            Q(organiser_type="campus", org_id_id=campus_id) |
            Q(organiser_type="campus_ig", ci_org_id_id=campus_id)
        ).values_list("event_id", flat=True)

        scoped = EventScope.objects.filter(
            Q(scope="campus", target_org_id_id=campus_id) |
            Q(scope="campus_ig", target_ci_org_id_id=campus_id)
        ).values_list("event_id", flat=True)

        collaborated = EventCollaborator.objects.filter(
            Q(collaborator_type="campus", org_id_id=campus_id) |
            Q(collaborator_type="campus_ig", ci_org_id_id=campus_id),
            invite_status="accepted",
        ).values_list("event_id", flat=True)

        return set(organised) | set(scoped) | set(collaborated)

    @staticmethod
    def _events_for_company(company_id):
        """Events organised by or collaborated with a company."""
        organised = EventOrganiser.objects.filter(
            organiser_type="company", org_id_id=company_id,
        ).values_list("event_id", flat=True)

        collaborated = EventCollaborator.objects.filter(
            collaborator_type="company", org_id_id=company_id,
            invite_status="accepted",
        ).values_list("event_id", flat=True)

        return set(organised) | set(collaborated)

    @staticmethod
    def _events_for_cluster(cluster):
        """Events from all IGs in a cluster."""
        ig_ids = list(
            InterestGroup.objects.filter(cluster=cluster)
            .values_list("id", flat=True)
        )
        if not ig_ids:
            return set()

        organised = EventOrganiser.objects.filter(
            Q(organiser_type="global_ig", ig_id_id__in=ig_ids) |
            Q(organiser_type="campus_ig", ci_ig_id_id__in=ig_ids)
        ).values_list("event_id", flat=True)

        collaborated = EventCollaborator.objects.filter(
            Q(collaborator_type="ig", ig_id_id__in=ig_ids) |
            Q(collaborator_type="campus_ig", ci_ig_id_id__in=ig_ids),
            invite_status="accepted",
        ).values_list("event_id", flat=True)

        return set(organised) | set(collaborated)


class EventFeaturedAPI(APIView):
    """GET events/featured/ — homepage slider, no auth."""

    def get(self, request):
        events = (
            Event.objects
            .filter(
                is_featured=True,
                status__in=[Event.Status.PUBLISHED, Event.Status.ONGOING],
                deleted_at__isnull=True,
            )
            .order_by("-start_datetime")[:10]
        )
        serializer = EventListSerializer(events, many=True)
        return CustomResponse(response=serializer.data).get_success_response()


class EventDetailAPI(APIView):
    """GET events/:id/ — full event detail."""

    authentication_classes = [CustomizePermission]

    def get(self, request, event_id):
        event = (
            Event.objects
            .filter(id=event_id, deleted_at__isnull=True)
            .select_related("created_by")
            .first()
        )
        if not event:
            return CustomResponse(
                general_message="Event not found"
            ).get_failure_response()

        # Only show non-published events to owners/admins
        if event.status not in (Event.Status.PUBLISHED, Event.Status.ONGOING, Event.Status.COMPLETED):
            try:
                user_id = JWTUtils.fetch_user_id(request)
            except Exception:
                return CustomResponse(
                    general_message="Event not found"
                ).get_failure_response()

            from .permissions import is_event_owner_or_coowner, is_admin
            if not is_event_owner_or_coowner(user_id, event) and not is_admin(user_id):
                return CustomResponse(
                    general_message="Event not found"
                ).get_failure_response()

        user_id = None
        try:
            user_id = JWTUtils.fetch_user_id(request)
        except Exception:
            pass

        serializer = EventDetailSerializer(event, context={"user_id": user_id})
        return CustomResponse(response=serializer.data).get_success_response()


class EventInterestAPI(APIView):
    """POST/DELETE events/:id/interest/ — "I'm Going" toggle."""

    authentication_classes = [CustomizePermission]

    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)

        event = Event.objects.filter(
            id=event_id,
            status__in=[Event.Status.PUBLISHED, Event.Status.ONGOING],
            deleted_at__isnull=True,
        ).first()
        if not event:
            return CustomResponse(
                general_message="Event not found"
            ).get_failure_response()

        if EventInterest.objects.filter(event=event, user_id=user_id).exists():
            return CustomResponse(
                general_message="You have already expressed interest in this event"
            ).get_failure_response()

        EventInterest.objects.create(
            id=str(uuid.uuid4()),
            event=event,
            user_id=user_id,
            expressed_at=DateTimeUtils.get_current_utc_time(),
        )

        return CustomResponse(
            general_message="Interest expressed successfully"
        ).get_success_response()

    def delete(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)

        interest = EventInterest.objects.filter(
            event_id=event_id, user_id=user_id
        ).first()
        if not interest:
            return CustomResponse(
                general_message="Interest not found"
            ).get_failure_response()

        interest.delete()

        return CustomResponse(
            general_message="Interest removed successfully"
        ).get_success_response()
