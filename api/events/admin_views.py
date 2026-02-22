"""
Admin event endpoints — approval, rejection, featuring.

GET   admin/events/              — all events, all statuses
POST  admin/events/:id/approve/  — approve pending event
POST  admin/events/:id/reject/   — reject pending event → draft
PATCH admin/events/:id/feature/  — toggle homepage featured status
"""

from rest_framework.views import APIView

from db.event import Event
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils, DateTimeUtils
from .permissions import can_approve_event, can_reject_event, is_admin
from .serializers import EventListSerializer


class AdminEventListAPI(APIView):
    """GET admin/events/ — all events, all statuses, all types."""

    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        events = Event.objects.filter(
            deleted_at__isnull=True
        ).order_by("-created_at")

        # Optional status filter
        status = request.query_params.get("status")
        if status:
            events = events.filter(status=status)

        paginated = CommonUtils.get_paginated_queryset(
            events, request, search_fields=["title", "description"]
        )

        serializer = EventListSerializer(paginated.get("queryset"), many=True)

        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated.get("pagination"),
        )


class AdminEventApproveAPI(APIView):
    """POST admin/events/:id/approve/ — approve pending event."""

    authentication_classes = [CustomizePermission]

    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)

        event = Event.objects.filter(id=event_id, deleted_at__isnull=True).first()
        if not event:
            return CustomResponse(
                general_message="Event not found"
            ).get_failure_response()

        can, new_status = can_approve_event(user_id, event)
        if not can:
            return CustomResponse(
                general_message="You do not have permission to approve this event, "
                                f"or event is not in an approvable state (status: {event.status})"
            ).get_failure_response()

        now = DateTimeUtils.get_current_utc_time()
        event.status = new_status
        event.updated_by_id = user_id
        event.updated_at = now
        event.save()

        return CustomResponse(
            general_message=f"Event approved (new status: {new_status})"
        ).get_success_response()


class AdminEventRejectAPI(APIView):
    """POST admin/events/:id/reject/ — reject pending event → draft."""

    authentication_classes = [CustomizePermission]

    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)

        event = Event.objects.filter(id=event_id, deleted_at__isnull=True).first()
        if not event:
            return CustomResponse(
                general_message="Event not found"
            ).get_failure_response()

        if not can_reject_event(user_id, event):
            return CustomResponse(
                general_message="You do not have permission to reject this event, "
                                f"or event is not in a rejectable state (status: {event.status})"
            ).get_failure_response()

        now = DateTimeUtils.get_current_utc_time()
        event.status = Event.Status.DRAFT
        event.updated_by_id = user_id
        event.updated_at = now
        event.save()

        return CustomResponse(
            general_message="Event rejected and returned to draft"
        ).get_success_response()


class AdminEventFeatureAPI(APIView):
    """PATCH admin/events/:id/feature/ — toggle homepage featured status."""

    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)

        event = Event.objects.filter(id=event_id, deleted_at__isnull=True).first()
        if not event:
            return CustomResponse(
                general_message="Event not found"
            ).get_failure_response()

        event.is_featured = not event.is_featured
        event.updated_by_id = user_id
        event.updated_at = DateTimeUtils.get_current_utc_time()
        event.save()

        status_msg = "featured" if event.is_featured else "unfeatured"
        return CustomResponse(
            general_message=f"Event {status_msg} successfully"
        ).get_success_response()
