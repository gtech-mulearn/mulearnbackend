"""
Scoped event feeds — entity-specific event listings.

GET ig/:ig_id/events/                  — IG dashboard event feed
GET ig/cluster/:cluster/events/        — cluster event feed
GET campus/:campus_id/events/          — campus page event list
GET campus-ig/:campus_ig_id/events/    — campus IG chapter events
GET company/:company_id/events/        — company event feed
"""

from django.db.models import Q
from rest_framework.views import APIView

from db.event import Event, EventCollaborator, EventOrganiser, EventScope
from utils.response import CustomResponse
from utils.utils import CommonUtils
from .serializers import EventListSerializer


def _published_events_base():
    """Common queryset for published/ongoing events, not deleted."""
    return Event.objects.filter(
        status__in=[Event.Status.PUBLISHED, Event.Status.ONGOING],
        deleted_at__isnull=True,
    )


class IGEventListAPI(APIView):
    """GET ig/:ig_id/events/ — events organized by or scoped to this IG."""

    def get(self, request, ig_id):
        # Events organised by this IG
        organised_ids = EventOrganiser.objects.filter(
            Q(organiser_type='global_ig', ig_id_id=ig_id) |
            Q(organiser_type='campus_ig', ci_ig_id_id=ig_id)
        ).values_list("event_id", flat=True)

        # Events scoped to this IG
        scoped_ids = EventScope.objects.filter(
            Q(scope='ig', target_ig_id_id=ig_id) |
            Q(scope='campus_ig', target_ci_ig_id_id=ig_id)
        ).values_list("event_id", flat=True)

        # Events where this IG is a collaborator
        collab_ids = EventCollaborator.objects.filter(
            Q(collaborator_type='ig', ig_id_id=ig_id),
            invite_status='accepted',
        ).values_list("event_id", flat=True)

        all_ids = set(organised_ids) | set(scoped_ids) | set(collab_ids)

        events = _published_events_base().filter(
            id__in=all_ids
        ).order_by("-start_datetime")

        paginated = CommonUtils.get_paginated_queryset(
            events, request, search_fields=["title"]
        )
        serializer = EventListSerializer(paginated.get("queryset"), many=True)
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated.get("pagination")
        )


class ClusterEventListAPI(APIView):
    """GET ig/cluster/:cluster/events/ — events for IGs in this cluster."""

    def get(self, request, cluster):
        # IGs in this cluster
        from db.task import InterestGroup
        ig_ids = list(
            InterestGroup.objects.filter(cluster=cluster)
            .values_list("id", flat=True)
        )
        if not ig_ids:
            return CustomResponse(response=[]).get_success_response()

        organised_ids = EventOrganiser.objects.filter(
            Q(organiser_type='global_ig', ig_id_id__in=ig_ids) |
            Q(organiser_type='campus_ig', ci_ig_id_id__in=ig_ids)
        ).values_list("event_id", flat=True)

        events = _published_events_base().filter(
            id__in=organised_ids
        ).order_by("-start_datetime")

        paginated = CommonUtils.get_paginated_queryset(
            events, request, search_fields=["title"]
        )
        serializer = EventListSerializer(paginated.get("queryset"), many=True)
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated.get("pagination")
        )


class CampusEventListAPI(APIView):
    """GET campus/:campus_id/events/ — events organized by or scoped to this campus."""

    def get(self, request, campus_id):
        organised_ids = EventOrganiser.objects.filter(
            Q(organiser_type='campus', org_id_id=campus_id) |
            Q(organiser_type='campus_ig', ci_org_id_id=campus_id)
        ).values_list("event_id", flat=True)

        scoped_ids = EventScope.objects.filter(
            Q(scope='campus', target_org_id_id=campus_id) |
            Q(scope='campus_ig', target_ci_org_id_id=campus_id)
        ).values_list("event_id", flat=True)

        collab_ids = EventCollaborator.objects.filter(
            Q(collaborator_type='campus', org_id_id=campus_id),
            invite_status='accepted',
        ).values_list("event_id", flat=True)

        all_ids = set(organised_ids) | set(scoped_ids) | set(collab_ids)

        events = _published_events_base().filter(
            id__in=all_ids
        ).order_by("-start_datetime")

        paginated = CommonUtils.get_paginated_queryset(
            events, request, search_fields=["title"]
        )
        serializer = EventListSerializer(paginated.get("queryset"), many=True)
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated.get("pagination")
        )


class CampusIGEventListAPI(APIView):
    """GET campus-ig/events/ — events for a specific campus-IG chapter."""

    def get(self, request):
        org_id = request.query_params.get("org_id")
        ig_id = request.query_params.get("ig_id")

        if not org_id or not ig_id:
            return CustomResponse(
                general_message="Both org_id and ig_id are required"
            ).get_failure_response()

        organised_ids = EventOrganiser.objects.filter(
            organiser_type='campus_ig',
            ci_org_id_id=org_id,
            ci_ig_id_id=ig_id,
        ).values_list("event_id", flat=True)

        scoped_ids = EventScope.objects.filter(
            scope='campus_ig',
            target_ci_org_id_id=org_id,
            target_ci_ig_id_id=ig_id,
        ).values_list("event_id", flat=True)

        all_ids = set(organised_ids) | set(scoped_ids)

        events = _published_events_base().filter(
            id__in=all_ids
        ).order_by("-start_datetime")

        paginated = CommonUtils.get_paginated_queryset(
            events, request, search_fields=["title"]
        )
        serializer = EventListSerializer(paginated.get("queryset"), many=True)
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated.get("pagination")
        )


class CompanyEventListAPI(APIView):
    """GET company/:company_id/events/ — events by this company."""

    def get(self, request, company_id):
        organised_ids = EventOrganiser.objects.filter(
            organiser_type='company',
            org_id_id=company_id,
        ).values_list("event_id", flat=True)

        collab_ids = EventCollaborator.objects.filter(
            collaborator_type='company',
            org_id_id=company_id,
            invite_status='accepted',
        ).values_list("event_id", flat=True)

        all_ids = set(organised_ids) | set(collab_ids)

        events = _published_events_base().filter(
            id__in=all_ids
        ).order_by("-start_datetime")

        paginated = CommonUtils.get_paginated_queryset(
            events, request, search_fields=["title"]
        )
        serializer = EventListSerializer(paginated.get("queryset"), many=True)
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated.get("pagination")
        )
