"""
Partner dashboard views — partner-facing endpoints (1–6).
"""
from django.db.models import Case, CharField, Count, Q, Value, When
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from db.events import Event, EventConnection
from db.partner import UserPartner
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.types import RoleType
from utils.response import CustomResponse
from utils.utils import CommonUtils, DateTimeUtils

from . import serializers


def _get_verified_partner(user_id):
    """Return the verified UserPartner for this user or None."""
    return UserPartner.objects.filter(user_link_id=user_id, status="verified").first()


class PartnerRegisterAPI(APIView):
    """
    POST  — submit a new partner registration.
    PATCH — update a pending or rejected registration (resets rejected → pending).
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Partner"],
        description="Submit a new partner registration for the authenticated user.",
        request=serializers.PartnerRegisterSerializer,
        responses={200: serializers.PartnerDetailSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if UserPartner.objects.filter(user_link_id=user_id).exists():
            return CustomResponse(
                general_message="A partner registration already exists for your account."
            ).get_failure_response()

        serializer = serializers.PartnerRegisterSerializer(
            data=request.data, context={"user_id": user_id}
        )
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        partner = serializer.save()
        return CustomResponse(
            general_message="Partner registration submitted successfully.",
            response=serializers.PartnerDetailSerializer(partner).data,
        ).get_success_response()

    @extend_schema(
        tags=["Dashboard - Partner"],
        description="Update a pending or rejected partner registration.",
        request=serializers.PartnerUpdateSerializer,
        responses={200: serializers.PartnerDetailSerializer},
    )
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        partner = UserPartner.objects.filter(user_link_id=user_id).first()

        if not partner:
            return CustomResponse(
                general_message="No partner registration found for your account."
            ).get_failure_response(status_code=404)

        if partner.status == "verified":
            return CustomResponse(
                general_message="Your partner is already verified. Use the profile/ endpoint to update."
            ).get_failure_response()

        serializer = serializers.PartnerUpdateSerializer(
            partner, data=request.data, partial=True, context={"user_id": user_id}
        )
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        if partner.status == "rejected":
            serializer.save(status="pending", rejection_reason=None)
            msg = "Partner registration updated and resubmitted successfully."
        else:
            serializer.save()
            msg = "Partner registration updated successfully."

        return CustomResponse(
            general_message=msg,
            response=serializers.PartnerDetailSerializer(partner).data,
        ).get_success_response()


class PartnerStatusAPI(APIView):
    """GET /partner/status/ — registration status for any authenticated user."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Partner"],
        description="Check the onboarding status of the authenticated user's partner registration.",
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        partner = UserPartner.objects.filter(user_link_id=user_id).first()

        if not partner:
            return CustomResponse(
                general_message="No partner registration found for your account."
            ).get_failure_response(status_code=404)

        return CustomResponse(
            general_message="Partner status fetched successfully.",
            response={
                "status": partner.status,
                "rejection_reason": partner.rejection_reason,
                "submitted_at": partner.submitted_at,
                "verified_at": partner.verified_at,
            },
        ).get_success_response()


class PartnerSummaryAPI(APIView):
    """GET /partner/summary/ — high-level dashboard summary (verified partners only)."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Partner"],
        description="High-level dashboard summary for the logged-in partner.",
    )
    @role_required([RoleType.PARTNER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        partner = _get_verified_partner(user_id)

        if not partner:
            return CustomResponse(
                general_message="You do not have permission to access this resource."
            ).get_failure_response(status_code=403)

        # Events where partner is accepted collaborator
        collab_event_ids = EventConnection.objects.filter(
            entity_type=EventConnection.EntityType.COLLAB_PARTNER,
            entity_id=partner.id,
            invite_status=EventConnection.InviteStatus.ACCEPTED,
        ).values_list("event_id", flat=True)

        all_events = Event.objects.filter(
            Q(organiser_type=Event.OrganiserType.PARTNER, created_by_id=partner.user_link_id) |
            Q(id__in=collab_event_ids)
        )

        active_events = all_events.filter(
            status__in=[Event.Status.PUBLISHED, Event.Status.ONGOING]
        )

        total_learners = EventConnection.objects.filter(
            event__in=all_events,
            entity_type=EventConnection.EntityType.USER_TICKET,
        ).count()

        recent_qs = all_events.order_by("-start_datetime")[:5]
        recent_events = [
            {
                "id": e.id,
                "title": e.title,
                "start_datetime": e.start_datetime,
                "learner_count": EventConnection.objects.filter(
                    event_id=e.id,
                    entity_type=EventConnection.EntityType.USER_TICKET,
                ).count(),
            }
            for e in recent_qs
        ]

        return CustomResponse(
            general_message="Partner summary fetched successfully.",
            response={
                "partner": serializers.PartnerDetailSerializer(partner).data,
                "total_events": all_events.count(),
                "active_events": active_events.count(),
                "total_learners_engaged": total_learners,
                "recent_events": recent_events,
            },
        ).get_success_response()


class PartnerProfileAPI(APIView):
    """
    GET   /partner/profile/ — retrieve full profile.
    PATCH /partner/profile/ — update profile fields.
    Both require verified partner status.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Partner"],
        description="Retrieve the full profile of the logged-in partner.",
        responses={200: serializers.PartnerDetailSerializer},
    )
    @role_required([RoleType.PARTNER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        partner = _get_verified_partner(user_id)

        if not partner:
            return CustomResponse(
                general_message="Partner profile not found or access denied."
            ).get_failure_response(status_code=403)

        return CustomResponse(
            general_message="Partner profile fetched successfully.",
            response=serializers.PartnerDetailSerializer(partner).data,
        ).get_success_response()

    @extend_schema(
        tags=["Dashboard - Partner"],
        description="Update the logged-in partner's profile. name/slug/status are read-only after verification.",
        request=serializers.PartnerUpdateSerializer,
        responses={200: serializers.PartnerDetailSerializer},
    )
    @role_required([RoleType.PARTNER.value])
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        partner = _get_verified_partner(user_id)

        if not partner:
            return CustomResponse(
                general_message="Partner profile not found or access denied."
            ).get_failure_response(status_code=403)

        # Strip read-only fields silently
        mutable = request.data.copy()
        for ro_field in ("name", "slug", "status", "user_link_id"):
            mutable.pop(ro_field, None)

        serializer = serializers.PartnerUpdateSerializer(
            partner, data=mutable, partial=True, context={"user_id": user_id}
        )
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        serializer.save()
        return CustomResponse(
            general_message="Partner profile updated successfully.",
            response=serializers.PartnerDetailSerializer(partner).data,
        ).get_success_response()


class PublicPartnerProfileAPI(APIView):
    """GET /partner/profile/public/<slug>/ — public profile, no auth required."""
    permission_classes = []

    @extend_schema(
        tags=["Public - Partner"],
        description="Public-facing partner profile. Only verified partners are accessible.",
        responses={200: serializers.PublicPartnerProfileSerializer},
    )
    def get(self, request, slug):
        partner = UserPartner.objects.filter(slug=slug, status="verified").first()
        if not partner:
            return CustomResponse(
                general_message="Partner not found."
            ).get_failure_response(status_code=404)

        return CustomResponse(
            general_message="Public partner profile fetched successfully.",
            response=serializers.PublicPartnerProfileSerializer(partner).data,
        ).get_success_response()


class PartnerEventListAPI(APIView):
    """
    GET /partner/events/
    Lists all events where this partner is the organiser or an accepted collaborator.
    Supports ?status= and ?type=organiser|collaborator filters.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Partner Events"],
        description="List all events where this partner is the organiser or accepted collaborator.",
    )
    @role_required([RoleType.PARTNER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        partner = _get_verified_partner(user_id)

        if not partner:
            return CustomResponse(
                general_message="You do not have permission to access this resource."
            ).get_failure_response(status_code=403)

        collab_event_ids = list(
            EventConnection.objects.filter(
                entity_type=EventConnection.EntityType.COLLAB_PARTNER,
                entity_id=partner.id,
                invite_status=EventConnection.InviteStatus.ACCEPTED,
            ).values_list("event_id", flat=True)
        )

        events = Event.objects.filter(
            Q(organiser_type=Event.OrganiserType.PARTNER, created_by_id=partner.user_link_id) |
            Q(id__in=collab_event_ids)
        ).annotate(
            partner_role=Case(
                When(
                    organiser_type=Event.OrganiserType.PARTNER,
                    created_by_id=partner.user_link_id,
                    then=Value("organiser"),
                ),
                default=Value("collaborator"),
                output_field=CharField(),
            )
        )

        # Query param filters
        status_filter = request.query_params.get("status")
        type_filter = request.query_params.get("type")

        if status_filter:
            events = events.filter(status=status_filter)
        if type_filter == "organiser":
            events = events.filter(
                organiser_type=Event.OrganiserType.PARTNER,
                created_by_id=partner.user_link_id,
            )
        elif type_filter == "collaborator":
            events = events.filter(id__in=collab_event_ids)

        paginated = CommonUtils.get_paginated_queryset(
            events.select_related("category"), request,
            search_fields=["title", "venue_city"],
            sort_fields={
                "start_datetime": "start_datetime",
                "created_at": "-created_at",
            },
        )

        # Batch learner counts in one query (avoids N+1)
        page_events = list(paginated["queryset"])
        event_ids = [e.id for e in page_events]
        learner_counts = {
            row["event_id"]: row["cnt"]
            for row in EventConnection.objects.filter(
                event_id__in=event_ids,
                entity_type=EventConnection.EntityType.USER_TICKET,
            ).values("event_id").annotate(cnt=Count("id"))
        }

        data = []
        for event in page_events:
            data.append({
                "id": event.id,
                "title": event.title,
                "slug": event.slug,
                "status": event.status,
                "start_datetime": event.start_datetime,
                "end_datetime": event.end_datetime,
                "venue_type": event.venue_type,
                "venue_city": event.venue_city,
                "cover_image": event.cover_image,
                "partner_role": event.partner_role,
                "learner_count": learner_counts.get(event.id, 0),
            })

        return CustomResponse(
            general_message="Events fetched successfully.",
            response={
                "data": data,
                "pagination": paginated["pagination"],
            },
        ).get_success_response()
