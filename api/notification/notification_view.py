from datetime import datetime, time

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.views import APIView
from rest_framework import status

from db.notification import Notification, BroadcastNotification
from db.events import EventConnection, EventInterest
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from . import serializers
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s

ALLOWED_SORT_FIELDS = {'created_at', '-created_at'}


def _parse_range_date(raw, end_of_day=False):
    """
    Parses an ISO date or datetime query param into a timezone-aware datetime.
    A date-only value ("2026-08-14") is expanded to the start/end of that day
    so fromDate/toDate behave as an inclusive range. Returns None for missing
    or unparseable input — an invalid filter is dropped rather than raising.
    """
    if not raw:
        return None
    dt = parse_datetime(raw)
    if dt is None:
        d = parse_date(raw)
        if d is None:
            return None
        dt = datetime.combine(d, time.max if end_of_day else time.min)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _notification_not_found():
    """
    404, not the CustomResponse default of 400. Ownership-isolation is a hard
    requirement here (PRD §7): a non-owned or missing notification id must
    return 404, never 403/400, so its existence is never disclosed by status
    code alone.
    """
    return CustomResponse(general_message='Notification not found').get_failure_response(
        status_code=404, http_status_code=status.HTTP_404_NOT_FOUND
    )


# ─────────────────────────────────────────────────────────────────────────────
# v2 USER-FACING VIEWS  (PRD §7)
# All views below work against the new notification table schema.
# ─────────────────────────────────────────────────────────────────────────────

class NotificationListView(APIView):
    """
    GET /api/v1/notification/

    Returns the authenticated user's notification feed.
    Supports optional query params:
        isRead (or is_read)     = true | false
        type                    = e.g. LC_JOIN_APPROVED — repeatable: ?type=A&type=B
        category                = e.g. LC
        fromDate (or from_date) = ISO date/datetime — inclusive lower bound on created_at
        toDate (or to_date)     = ISO date/datetime — inclusive upper bound on created_at
        sortBy (or sort_by)     = 'created_at' | '-created_at' (default '-created_at')
        page                    = page number (default 1)
        page_size               = results per page (default 20, max 100)
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="List notifications for the authenticated user.")
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        params  = request.query_params

        qs = Notification.objects.filter(user_id=user_id, is_archived=False)

        # Optional filters
        is_read     = params.get('isRead', params.get('is_read'))
        notif_types = params.getlist('type')
        category    = params.get('category')
        from_date   = _parse_range_date(params.get('fromDate', params.get('from_date')))
        to_date     = _parse_range_date(params.get('toDate', params.get('to_date')), end_of_day=True)
        sort_by     = params.get('sortBy', params.get('sort_by', '-created_at'))

        if is_read is not None:
            qs = qs.filter(is_read=(is_read.lower() == 'true'))
        if notif_types:
            qs = qs.filter(type__in=notif_types)
        if category:
            qs = qs.filter(category=category)
        if from_date:
            qs = qs.filter(created_at__gte=from_date)
        if to_date:
            qs = qs.filter(created_at__lte=to_date)

        # Whitelisted — sort_by is user input and must never reach order_by() raw
        qs = qs.order_by(sort_by if sort_by in ALLOWED_SORT_FIELDS else '-created_at')

        # Simple pagination
        try:
            page      = max(1, int(params.get('page', 1)))
            page_size = min(100, max(1, int(params.get('page_size', 20))))
        except ValueError:
            page, page_size = 1, 20

        offset     = (page - 1) * page_size
        total      = qs.count()
        page_qs    = qs.select_related('actor')[offset: offset + page_size]

        return CustomResponse(response={
            'count':      total,
            'page':       page,
            'page_size':  page_size,
            'results':    serializers.NotificationSerializer(page_qs, many=True).data,
        }).get_success_response()


class UnreadCountView(APIView):
    """
    GET /api/v1/notification/unread-count/

    Returns the number of unread, non-archived notifications for the user.
    Phase 1: direct SQL COUNT (no Redis).
    Phase 2: Redis-backed with SQL fallback.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Get unread notification count.")
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        count = Notification.objects.filter(
            user_id=user_id, is_read=False, is_archived=False
        ).count()
        return CustomResponse(response={'unread_count': count}).get_success_response()


class MarkReadView(APIView):
    """
    PATCH /api/v1/notification/<notification_id>/read/

    Marks a single notification as read.
    Returns 404 (not 403) for IDs that don't belong to the requesting user —
    this prevents leaking whether another user's notification ID exists.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Mark a notification as read.")
    def patch(self, request, notification_id):
        user_id = JWTUtils.fetch_user_id(request)

        notification = Notification.objects.filter(
            id=notification_id, user_id=user_id
        ).first()

        if not notification:
            return _notification_not_found()

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at'])

        return CustomResponse(
            general_message='Notification marked as read'
        ).get_success_response()


class MarkReadBulkView(APIView):
    """
    PATCH /api/v1/notification/read/

    Marks a specific list of the caller's own notifications as read.
    Body: {"ids": ["<uuid>", ...]}

    IDs that don't exist or aren't owned by the caller are just not counted
    in the update — there's no single id here to 404 on the way the
    single-notification endpoints do, so the response reports how many of
    the submitted ids were actually matched and updated.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Mark a specific list of notifications as read.")
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        ids = request.data.get('ids')

        if not isinstance(ids, list) or not ids:
            return CustomResponse(general_message="'ids' must be a non-empty list").get_failure_response()

        updated = Notification.objects.filter(
            id__in=ids, user_id=user_id, is_read=False
        ).update(is_read=True, read_at=timezone.now())

        return CustomResponse(
            general_message=f'{updated} notification(s) marked as read'
        ).get_success_response()


class MarkAllReadView(APIView):
    """
    PATCH /api/v1/notification/read-all/

    Marks all unread notifications as read for the authenticated user.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Mark all notifications as read.")
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        now     = timezone.now()

        updated = Notification.objects.filter(
            user_id=user_id, is_read=False
        ).update(is_read=True, read_at=now)

        return CustomResponse(
            general_message=f'{updated} notification(s) marked as read'
        ).get_success_response()


class ArchiveView(APIView):
    """
    PATCH /api/v1/notification/<notification_id>/archive/

    Soft-hides the notification. It stays in the DB but is excluded
    from the default feed (is_archived=False filter).
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Archive a notification.")
    def patch(self, request, notification_id):
        user_id = JWTUtils.fetch_user_id(request)

        notification = Notification.objects.filter(
            id=notification_id, user_id=user_id
        ).first()

        if not notification:
            return _notification_not_found()

        notification.is_archived = True
        notification.save(update_fields=['is_archived'])

        return CustomResponse(
            general_message='Notification archived'
        ).get_success_response()


class DeleteOneView(APIView):
    """
    DELETE /api/v1/notification/<notification_id>/

    Hard-deletes a single notification scoped to the requesting user.
    Returns 404 for non-owned IDs — never 403 — to avoid leaking existence.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Delete a single notification.")
    def delete(self, request, notification_id):
        user_id = JWTUtils.fetch_user_id(request)

        notification = Notification.objects.filter(
            id=notification_id, user_id=user_id
        ).first()

        if not notification:
            return _notification_not_found()

        notification.delete()
        return CustomResponse(
            general_message='Notification deleted'
        ).get_success_response()


class DeleteAllView(APIView):
    """
    DELETE /api/v1/notification/

    Hard-deletes ALL notifications for the authenticated user.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Delete all notifications for the current user.")
    def delete(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        deleted_count, _ = Notification.objects.filter(user_id=user_id).delete()
        return CustomResponse(
            general_message=f'{deleted_count} notification(s) deleted'
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY BROADCAST HELPERS  (kept — broadcast system still active)
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_user_broadcasts(user_id: str):
    """
    Return active (non-expired) BroadcastNotification rows the user qualifies for.
    Audience matching logic per target_type:
        'global'          -> always included
        'campus'          -> user is linked to that org (UserOrganizationLink)
        'interest_group'  -> user has an active LEARNER link to that IG (UserIgLink)
        'campus_ig'       -> user has an active LEARNER link and is in that campus org
        'event_interest'  -> user has expressed interest in that event (EventInterest)
        'event_coowners'  -> user is the event creator OR a CO_OWNER EventConnection
    """
    from db.organization import UserOrganizationLink
    from db.task import UserIgLink

    now             = timezone.now()
    active_broadcasts = BroadcastNotification.objects.filter(expires_at__gt=now)

    campus_org_ids = set(
        UserOrganizationLink.objects.filter(user_id=user_id, verified=True)
        .values_list('org_id', flat=True)
    )
    learner_ig_ids = set(
        UserIgLink.objects.filter(
            user_id=user_id,
            assignment_type=UserIgLink.AssignmentType.LEARNER,
            is_active=True,
        ).values_list('ig_id', flat=True)
    )
    interested_event_ids = set(
        EventInterest.objects.filter(user_id=user_id).values_list('event_id', flat=True)
    )
    coowned_event_ids = set(
        EventConnection.objects.filter(
            entity_id=user_id,
            entity_type=EventConnection.EntityType.CO_OWNER,
        ).values_list('event_id', flat=True)
    )
    from db.events import Event
    created_event_ids  = set(
        Event.objects.filter(created_by_id=user_id).values_list('id', flat=True)
    )
    event_coowner_ids = coowned_event_ids | created_event_ids

    matched = []
    for b in active_broadcasts:
        tt  = b.target_type
        tid = b.target_id
        if tt == 'global':
            matched.append(b)
        elif tt == 'campus' and tid in campus_org_ids:
            matched.append(b)
        elif tt == 'interest_group' and tid in learner_ig_ids:
            matched.append(b)
        elif tt == 'campus_ig':
            from db.campus import CampusIGChapter
            chapter = CampusIGChapter.objects.filter(id=tid).first()
            if chapter and chapter.org_id in campus_org_ids and chapter.ig_id in learner_ig_ids:
                matched.append(b)
        elif tt == 'event_interest' and tid in interested_event_ids:
            matched.append(b)
        elif tt == 'event_coowners' and tid in event_coowner_ids:
            matched.append(b)

    return matched


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY BROADCAST VIEWS  (kept — endpoints still active)
# ─────────────────────────────────────────────────────────────────────────────

class BroadcastNotificationDeleteAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Delete a broadcast notification. Admin only.")
    @role_required([RoleType.ADMIN.value])
    def delete(self, request, broadcast_id):
        try:
            broadcast = BroadcastNotification.objects.get(id=broadcast_id)
        except BroadcastNotification.DoesNotExist:
            return CustomResponse(general_message='Broadcast notification not found').get_failure_response()
        broadcast.delete()
        return CustomResponse(general_message='Broadcast notification deleted successfully').get_success_response()


class BroadcastNotificationDeleteAllAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Delete all broadcast notifications. Admin only.")
    @role_required([RoleType.ADMIN.value])
    def delete(self, request):
        broadcasts = BroadcastNotification.objects.all()
        if not broadcasts.exists():
            return CustomResponse(general_message='No broadcast notifications to delete').get_failure_response()
        count = broadcasts.count()
        broadcasts.delete()
        return CustomResponse(general_message=f'All {count} broadcast notification(s) deleted successfully').get_success_response()


class BroadcastNotificationListAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Admin only. List all broadcast notifications.")
    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        broadcasts = BroadcastNotification.objects.select_related('created_by').all()
        data = serializers.BroadcastNotificationAdminSerializer(broadcasts, many=True).data
        return CustomResponse(response=data).get_success_response()


class BroadcastNotificationCreateAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Admin only. Create a new global broadcast announcement.")
    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        write_serializer = serializers.BroadcastNotificationWriteSerializer(data=request.data)

        if not write_serializer.is_valid():
            return CustomResponse(general_message=write_serializer.errors).get_failure_response()

        from db.user import User as UserModel
        from utils.utils import DateTimeUtils
        creator = UserModel.objects.filter(id=user_id).first()
        if not creator:
            return CustomResponse(general_message='User not found').get_failure_response()

        broadcast = BroadcastNotification.objects.create(
            title=write_serializer.validated_data['title'],
            description=write_serializer.validated_data['description'],
            url=write_serializer.validated_data.get('url'),
            target_type='global',
            target_id=None,
            created_by=creator,
            created_at=DateTimeUtils.get_current_utc_time(),
            expires_at=write_serializer.validated_data['expires_at'],
        )
        return CustomResponse(
            general_message='Broadcast notification created successfully.',
            response=serializers.BroadcastNotificationAdminSerializer(broadcast).data,
        ).get_success_response()


class BroadcastNotificationUpdateAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Admin only. Partially update a broadcast notification.")
    @role_required([RoleType.ADMIN.value])
    def patch(self, request, broadcast_id):
        try:
            broadcast = BroadcastNotification.objects.get(id=broadcast_id)
        except BroadcastNotification.DoesNotExist:
            return CustomResponse(general_message='Broadcast notification not found').get_failure_response()

        write_serializer = serializers.BroadcastNotificationWriteSerializer(
            instance=broadcast, data=request.data, partial=True
        )
        if not write_serializer.is_valid():
            return CustomResponse(general_message=write_serializer.errors).get_failure_response()

        write_serializer.save()
        return CustomResponse(
            general_message='Broadcast notification updated successfully.',
            response=serializers.BroadcastNotificationAdminSerializer(broadcast).data,
        ).get_success_response()
