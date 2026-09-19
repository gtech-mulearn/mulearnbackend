from datetime import datetime, time, timedelta

from django.db.models import CharField, Exists, F, OuterRef, Q, Subquery, Value
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.views import APIView
from rest_framework import status

from db.notification import Notification, BroadcastNotification, BroadcastNotificationRead
from db.events import EventConnection, EventInterest
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import DateTimeUtils
from .audience import Audience
from .notifications_utils import get_unread_count, invalidate_unread_count
from .service import NotificationService
from .types import NotificationType
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

    Returns the authenticated user's merged feed — personal `notification`
    rows and any `broadcast_notification` rows the user's audience membership
    matches (campus/IG/event/global) — as one created_at-ordered, paginated
    list. Each result carries `source` ('personal' | 'broadcast') so the
    client knows which id-space a row's id belongs to for read/archive calls.

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

        is_read_param = params.get('isRead', params.get('is_read'))
        is_read     = (is_read_param.lower() == 'true') if is_read_param is not None else None
        notif_types = params.getlist('type')
        category    = params.get('category')
        from_date   = _parse_range_date(params.get('fromDate', params.get('from_date')))
        to_date     = _parse_range_date(params.get('toDate', params.get('to_date')), end_of_day=True)
        sort_by     = params.get('sortBy', params.get('sort_by', '-created_at'))

        qs = get_merged_feed_queryset(
            user_id,
            is_read=is_read, notif_types=notif_types, category=category,
            from_date=from_date, to_date=to_date,
        )
        # Whitelisted — sort_by is user input and must never reach order_by() raw
        if sort_by not in ALLOWED_SORT_FIELDS:
            sort_by = '-created_at'
        qs = qs.order_by(('-' if sort_by.startswith('-') else '') + 'f_created_at')

        # Simple pagination
        try:
            page      = max(1, int(params.get('page', 1)))
            page_size = min(100, max(1, int(params.get('page_size', 20))))
        except ValueError:
            page, page_size = 1, 20

        offset = (page - 1) * page_size
        total  = qs.count()
        rows   = list(qs[offset: offset + page_size])

        results = [
            {
                'id':          str(r['f_id']),
                'type':        r['f_type'],
                'category':    r['f_category'],
                'title':       r['f_title'],
                'description': r['f_description'],
                'entity_type': r['f_entity_type'],
                'entity_id':   r['f_entity_id'],
                'is_read':     bool(r['f_is_read']),
                'is_archived': bool(r['f_is_archived']),
                'created_at':  r['f_created_at'],
                'read_at':     r['f_read_at'],
                'source':      r['f_source'],
                'redirect_url': r['f_redirect_url'],
            }
            for r in rows
        ]

        return CustomResponse(response={
            'count':      total,
            'page':       page,
            'page_size':  page_size,
            'results':    results,
        }).get_success_response()


class UnreadCountView(APIView):
    """
    GET /api/v1/notification/unread-count/

    Returns the number of unread, non-archived personal notifications for the
    user. Redis cache-aside (notif:unread:{user_id}, TTL =
    NOTIFICATION_UNREAD_COUNT_CACHE_TTL) in front of the indexed COUNT query;
    every write path that changes a user's unread set invalidates the key.

    Counts personal `notification` rows only — broadcasts have no per-user
    read state to aggregate here without an anti-join against
    broadcast_notification_read on the hottest endpoint in the system, which
    is the exact cost the row-per-user path exists to avoid. A broadcast's
    unread-ness is only meaningful in the merged feed itself (NotificationListView).
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Get unread notification count.")
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        count = get_unread_count(user_id)
        return CustomResponse(response={'unread_count': count}).get_success_response()


class MarkReadView(APIView):
    """
    PATCH /api/v1/notification/<notification_id>/read/

    Marks a single item as read. `notification_id` may be either a personal
    `notification` row or a `broadcast_notification` row the caller's
    audience matches — checked in that order. A broadcast has no per-user
    row to mutate, so "marking it read" writes a sparse read receipt into
    broadcast_notification_read instead (get_or_create — idempotent, a
    second read never double-writes).

    Returns 404 (not 403) for IDs that don't belong to / aren't visible to
    the requesting user — this prevents leaking whether another user's
    notification ID exists.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Mark a notification as read.")
    def patch(self, request, notification_id):
        user_id = JWTUtils.fetch_user_id(request)

        notification = Notification.objects.filter(
            id=notification_id, user_id=user_id
        ).first()

        if notification:
            if not notification.is_read:
                notification.is_read = True
                notification.read_at = timezone.now()
                notification.save(update_fields=['is_read', 'read_at'])
                invalidate_unread_count(user_id)

            return CustomResponse(
                general_message='Notification marked as read'
            ).get_success_response()

        broadcast = BroadcastNotification.objects.filter(
            id=notification_id, expires_at__gt=timezone.now(),
        ).first()

        if not broadcast:
            return _notification_not_found()

        receipt, created = BroadcastNotificationRead.objects.get_or_create(
            broadcast_id=broadcast.id, user_id=user_id,
            defaults={'read_at': timezone.now()},
        )
        if not created and not receipt.read_at:
            receipt.read_at = timezone.now()
            receipt.save(update_fields=['read_at'])

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

        if updated:
            invalidate_unread_count(user_id)

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

        if updated:
            invalidate_unread_count(user_id)

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
        if not notification.is_read:
            invalidate_unread_count(user_id)

        return CustomResponse(
            general_message='Notification archived'
        ).get_success_response()


class DeleteOneView(APIView):
    """
    DELETE /api/v1/notification/<notification_id>/

    Soft-deletes a single item scoped to the requesting user, personal or
    broadcast — checked in that order (same lookup pattern as MarkReadView).
    Users get no hard-delete path for either source; the underlying row
    always survives.

    Personal: sets Notification.is_archived=True, same as ArchiveView. Row
    stays in the DB (retention cron / expires_at, any future audit need) and
    drops out of the default feed (is_archived=False filter).

    Broadcast: a shared broadcast_notification row can't be archived per-user
    by mutating it (every other recipient shares that row) — instead this
    sets archived_at on that user's own BroadcastNotificationRead row,
    mirroring the read-receipt (get_or_create, then only touch archived_at if
    it isn't already set — idempotent, a second delete doesn't bump the
    timestamp).

    Returns 404 for non-owned/non-matching IDs — never 403 — to avoid
    leaking existence.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Delete (soft) a single notification.")
    def delete(self, request, notification_id):
        user_id = JWTUtils.fetch_user_id(request)

        notification = Notification.objects.filter(
            id=notification_id, user_id=user_id
        ).first()

        if notification:
            was_unread = not notification.is_read
            if not notification.is_archived:
                notification.is_archived = True
                notification.save(update_fields=['is_archived'])
                if was_unread:
                    invalidate_unread_count(user_id)

            return CustomResponse(
                general_message='Notification deleted'
            ).get_success_response()

        broadcast = BroadcastNotification.objects.filter(
            id=notification_id, expires_at__gt=timezone.now(),
        ).first()

        if not broadcast:
            return _notification_not_found()

        now = timezone.now()
        receipt, created = BroadcastNotificationRead.objects.get_or_create(
            broadcast_id=broadcast.id, user_id=user_id,
            defaults={'archived_at': now},
        )
        if not created and not receipt.archived_at:
            receipt.archived_at = now
            receipt.save(update_fields=['archived_at'])

        return CustomResponse(
            general_message='Notification deleted'
        ).get_success_response()


class DeleteAllView(APIView):
    """
    DELETE /api/v1/notification/

    Soft-deletes ALL notifications for the authenticated user — sets
    is_archived=True on every currently non-archived row, same rationale as
    DeleteOneView. Idempotent: re-running only affects rows that are still
    is_archived=False, so it never double-counts or errors on a repeat call.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Delete (soft) all notifications for the current user.")
    def delete(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        deleted_count = Notification.objects.filter(
            user_id=user_id, is_archived=False
        ).update(is_archived=True)
        if deleted_count:
            invalidate_unread_count(user_id)

        return CustomResponse(
            general_message=f'{deleted_count} notification(s) deleted'
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# MERGED FEED  (notification ∪ broadcast_notification, scoped to :user_id)
#
# Replaces the old _resolve_user_broadcasts() Python loop over every active
# broadcast row (an unbounded scan — CLAUDE.md: never return an unbounded
# queryset) with a single scoped SQL query per source table, matching the
# user's audience membership via indexed subqueries instead of Python `in`
# checks, then combining both with UNION ALL and paginating the merged result.
# ─────────────────────────────────────────────────────────────────────────────

def _broadcast_audience_q(user_id: str) -> Q:
    """
    The same target_type matching rules as the old per-row Python loop,
    expressed as one filter so it runs as indexed subqueries inside the
    broadcast_notification query instead of a full-table Python scan:
        'global'          -> always included
        'campus'          -> user is linked to that org (UserOrganizationLink)
        'interest_group'  -> user has an active LEARNER link to that IG (UserIgLink)
        'campus_ig'       -> user has an active LEARNER link and is in that campus org
        'event_interest'  -> user has expressed interest in that event (EventInterest)
        'event_coowners'  -> user is the event creator OR a CO_OWNER EventConnection
    """
    from db.organization import UserOrganizationLink
    from db.task import UserIgLink
    from db.campus import CampusIGChapter
    from db.events import Event

    campus_org_ids = UserOrganizationLink.objects.filter(
        user_id=user_id, verified=True
    ).values('org_id')
    learner_ig_ids = UserIgLink.objects.filter(
        user_id=user_id,
        assignment_type=UserIgLink.AssignmentType.LEARNER,
        is_active=True,
    ).values('ig_id')
    campus_ig_chapter_ids = CampusIGChapter.objects.filter(
        org_id__in=campus_org_ids, ig_id__in=learner_ig_ids
    ).values('id')
    interested_event_ids = EventInterest.objects.filter(user_id=user_id).values('event_id')
    coowned_event_ids = EventConnection.objects.filter(
        entity_id=user_id, entity_type=EventConnection.EntityType.CO_OWNER,
    ).values('event_id')
    created_event_ids = Event.objects.filter(created_by_id=user_id).values('id')

    return (
        Q(target_type='global')
        | Q(target_type='campus', target_id__in=campus_org_ids)
        | Q(target_type='interest_group', target_id__in=learner_ig_ids)
        | Q(target_type='campus_ig', target_id__in=campus_ig_chapter_ids)
        | Q(target_type='event_interest', target_id__in=interested_event_ids)
        | Q(target_type='event_coowners', target_id__in=coowned_event_ids)
        | Q(target_type='event_coowners', target_id__in=created_event_ids)
    )


# Aliased ('f_' prefix) rather than the bare column names: Django's ORM puts
# a values()/union() SELECT's *plain* model fields first and its *annotated*
# expressions last, regardless of the order passed to values() — and the two
# sides here have different fields be "plain" vs "annotated" (e.g. `type` is
# a real column on Notification but an F('notif_type') alias on
# BroadcastNotification). Annotating every single column, on both sides,
# under a name no model field already has, is what forces both SELECTs to
# actually emit these 13 columns in the same position — anything less and
# UNION ALL silently zips mismatched columns together.
_FEED_COLUMNS = [
    'f_id', 'f_type', 'f_category', 'f_title', 'f_description',
    'f_entity_type', 'f_entity_id', 'f_is_read', 'f_read_at',
    'f_is_archived', 'f_created_at', 'f_source', 'f_redirect_url',
]


def _personal_feed_qs(user_id: str):
    return Notification.objects.filter(
        user_id=user_id, is_archived=False,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    ).annotate(
        f_id=F('id'), f_type=F('type'), f_category=F('category'),
        f_title=F('title'), f_description=F('description'),
        f_entity_type=F('entity_type'), f_entity_id=F('entity_id'),
        f_is_read=F('is_read'), f_read_at=F('read_at'),
        f_is_archived=F('is_archived'), f_created_at=F('created_at'),
        f_source=Value('personal', output_field=CharField()),
        f_redirect_url=F('redirect_url'),
    ).values(*_FEED_COLUMNS)


def _broadcast_feed_qs(user_id: str):
    receipt = BroadcastNotificationRead.objects.filter(
        broadcast_id=OuterRef('id'), user_id=user_id,
    )
    # Split by which timestamp is set, not just row existence — a receipt row
    # can now exist for archive-only (read_at NULL, e.g. deleted without ever
    # being opened), so "a row exists" alone is no longer equivalent to "read".
    read_receipt = receipt.filter(read_at__isnull=False)
    archive_receipt = receipt.filter(archived_at__isnull=False)
    return BroadcastNotification.objects.filter(
        _broadcast_audience_q(user_id), expires_at__gt=timezone.now(),
    ).exclude(
        Exists(archive_receipt)
    ).annotate(
        f_id=F('id'), f_type=F('notif_type'), f_category=F('category'),
        f_title=F('title'), f_description=F('description'),
        f_entity_type=F('entity_type'), f_entity_id=F('entity_id'),
        f_is_read=Exists(read_receipt),
        f_read_at=Subquery(read_receipt.values('read_at')[:1]),
        f_is_archived=Exists(archive_receipt),
        f_created_at=F('created_at'),
        f_source=Value('broadcast', output_field=CharField()),
        f_redirect_url=F('url'),
    ).values(*_FEED_COLUMNS)


def _apply_feed_filters(qs, is_read, notif_types, category, from_date, to_date):
    if is_read is not None:
        qs = qs.filter(f_is_read=is_read)
    if notif_types:
        qs = qs.filter(f_type__in=notif_types)
    if category:
        qs = qs.filter(f_category=category)
    if from_date:
        qs = qs.filter(f_created_at__gte=from_date)
    if to_date:
        qs = qs.filter(f_created_at__lte=to_date)
    return qs


def get_merged_feed_queryset(
    user_id: str, *, is_read=None, notif_types=None, category=None,
    from_date=None, to_date=None,
):
    """
    One UNION ALL across both tables, scoped to :user_id via the indexed
    subqueries above — no unbounded scan, no per-row Python matching.

    Filters must be applied to each side BEFORE union() — Django doesn't
    support .filter() on an already-combined queryset. order_by()/count()/
    slicing on the combined result (done by the caller) are fine.
    """
    personal  = _apply_feed_filters(_personal_feed_qs(user_id),  is_read, notif_types, category, from_date, to_date)
    broadcast = _apply_feed_filters(_broadcast_feed_qs(user_id), is_read, notif_types, category, from_date, to_date)
    return personal.union(broadcast, all=True)


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


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN NOTIFICATION DISPATCH — new pipeline (dispatch()-backed, global only)
#
# Unlike the legacy BroadcastNotificationCreateAPI above (which writes
# BroadcastNotification directly with notif_type=None/category=None), this
# goes through NotificationService.dispatch() so the send gets a real
# NotificationType/Category (ADMIN_BROADCAST/ADMIN), the on_commit safety net,
# and consistent dedupe-key handling. Audience is GLOBAL only for now —
# targeted audiences (campus/IG/specific users) are a follow-up.
# ─────────────────────────────────────────────────────────────────────────────

class AdminBroadcastDispatchAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Admin only. Dispatch a global notification broadcast.")
    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = serializers.AdminBroadcastDispatchSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        data = serializer.validated_data
        expires_at = DateTimeUtils.get_current_utc_time() + timedelta(
            days=data.get('expires_in_days', 7)
        )

        NotificationService.dispatch(
            notif_type   = NotificationType.ADMIN_BROADCAST,
            audience     = Audience.all(),
            context      = {"title": data['title'], "body": data['description']},
            actor_id     = user_id,
            redirect_url = data.get('redirect_url'),
            expires_at   = expires_at,
        )

        return CustomResponse(
            general_message='Broadcast dispatched successfully.'
        ).get_success_response()
