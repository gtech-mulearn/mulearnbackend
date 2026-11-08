import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from django.conf import settings
from django.db import transaction

from api.notification.audience import Audience, AudienceResolver, AudienceSpec
from api.notification.templates import render_template
from api.notification.types import TYPE_META, NotificationType

logger = logging.getLogger(__name__)


def _plain(value):
    """
    Returns the raw string value of a (str, Enum) member, e.g. "LC_JOIN_REQUEST".

    NotificationType/Category are `class X(str, Enum)`. On Python 3.11+, Enum's
    __str__ was changed so f-strings and %-formatting on a member produce
    "NotificationType.LC_JOIN_REQUEST" instead of "LC_JOIN_REQUEST" — only
    plain concatenation and `.value` are unaffected. Route every place that
    builds a string (dedupe_key, log messages) through this so the corrupted
    form never leaks into a stored column or a log line.
    """
    return value.value if isinstance(value, Enum) else value


class NotificationService:
    """
    Single entry point for all notifications in the system.

    Producers call:
        NotificationService.dispatch(
            notif_type = NotificationType.LC_JOIN_APPROVED,
            audience   = Audience.user(user_id),
            context    = {"lc_name": "Web Dev Circle"},
            entity_id  = str(lc.id),
            occurrence = "1",
            actor_id   = str(request.user.id),
        )

    Rules:
    - dispatch() MUST be called inside the same DB transaction as the
      business action. Notifications are only written after that transaction
      commits. A rollback = zero notifications written.
    - The actor is always excluded from recipients.
    - Duplicate dispatches for the same (user, dedupe_key) are silently ignored.
    """

    _resolver = AudienceResolver()

    @classmethod
    def dispatch(
        cls,
        notif_type:  str,
        audience:    AudienceSpec,
        context:     dict,
        entity_id:   Optional[str] = None,
        occurrence:  str           = "1",
        actor_id:    Optional[str] = None,
        entity_type: Optional[str] = None,
        redirect_url: Optional[str] = None,
        expires_at:  Optional[datetime] = None,
    ) -> None:
        """
        Register a notification to be written after the current DB transaction commits.

        Args:
            notif_type:  NotificationType value e.g. NotificationType.LC_JOIN_APPROVED
            audience:    Who to notify — use Audience.user(), .users(), .lc_members() etc.
            context:     Template variables dict e.g. {"lc_name": "Web Dev Circle"}
            entity_id:   UUID of the entity this notification is about (for deep-linking)
            occurrence:  Discriminator for dedupe key — "1" for once-per-entity events,
                         entity.updated_at epoch for edit events, window id for reminders
            actor_id:    Who triggered the action — excluded from recipients
            entity_type: Override entity type string. If None, derived from notif_type.
            redirect_url: Deep-link URL — admin-broadcast use only today. Stored on
                         Notification.redirect_url / BroadcastNotification.url.
            expires_at:  Explicit expiry, overriding BroadcastUtils' EXPIRY_DAYS default —
                         admin-broadcast use only today (producers rely on the DB default).
        """

        # Normalize once — every downstream use (dedupe_key, storage, logging)
        # reads notif_type_str/category_str instead of the raw enum member.
        notif_type_str = _plain(notif_type)

        # ── Step 1: Look up type metadata ────────────────────────────────────
        meta = TYPE_META.get(notif_type)
        if not meta:
            logger.error(
                "dispatch: unknown NotificationType=%s — add it to TYPE_META in types.py",
                notif_type_str
            )
            return

        # ── Step 2: Validate template exists for IN_APP ───────────────────────
        # Render now (before on_commit) so template errors surface immediately
        # during the request, not silently later.
        rendered = render_template(notif_type, "IN_APP", context)
        if not rendered:
            logger.error(
                "dispatch: no IN_APP template for type=%s — add it to TEMPLATES in templates.py",
                notif_type_str
            )
            return

        category_str = _plain(meta.category)

        # Derive entity_type from notif_type if not provided. Keeps producers
        # clean — they don't need to know which entity type each notification
        # maps to. Add more mappings to _ENTITY_TYPE_MAP as modules are built.
        resolved_entity_type = entity_type or _ENTITY_TYPE_MAP.get(notif_type)

        # Build dedupe key — "type:entity_id:occurrence". None when entity_id
        # is not provided (safe — MySQL unique index allows NULLs). Shared
        # between both write paths below so a broadcast and a per-recipient
        # write for the same (type, entity, occurrence) can't both land.
        dedupe_key = (
            f"{notif_type_str}:{entity_id}:{occurrence}"
            if entity_id else None
        )

        # ── Step 3: Audience-size branch (hybrid fan-out) ──────────────────────
        # Large/global audiences write ONE broadcast_notification row instead
        # of fanning out to one notification row per recipient — this is what
        # actually avoids the 20k-row write, regardless of whether Celery is
        # running. NOTIFICATION_DISPATCH_MODE is a separate, later latency
        # dial for offloading the write itself, not what solves the row count.
        #
        # broadcast_target() only recognizes EVENT_SCOPE audiences today
        # (USER/USERS/LC_MEMBERS/LC_LEAD are inherently small and always take
        # the per-recipient path below). count() is a cheap COUNT(*)-style
        # check — it never materializes the full recipient id set, so this
        # branch decision itself doesn't pay the cost it's trying to avoid.
        broadcast_target = cls._resolver.broadcast_target(audience)
        if broadcast_target is not None:
            recipient_count = cls._resolver.count(audience, actor_id=actor_id)
            if recipient_count >= settings.NOTIFICATION_BROADCAST_THRESHOLD:
                target_type, target_id = broadcast_target
                transaction.on_commit(lambda: cls._write_broadcast(
                    notif_type   = notif_type_str,
                    category     = category_str,
                    rendered     = rendered,
                    context      = context,
                    entity_type  = resolved_entity_type,
                    entity_id    = entity_id,
                    actor_id     = actor_id,
                    dedupe_key   = dedupe_key,
                    target_type  = target_type,
                    target_id    = target_id,
                    url          = redirect_url,
                    expires_at   = expires_at,
                ))
                logger.debug(
                    "dispatch: registered on_commit broadcast for type=%s target_type=%s recipients~=%d",
                    notif_type_str, target_type, recipient_count
                )
                return

        # ── Step 4: Per-recipient path (small/scoped audiences) ────────────────
        # DB query runs here (e.g. fetches LC members from user_circle_link).
        # Actor is excluded inside resolve().
        recipient_ids = cls._resolver.resolve(audience, actor_id=actor_id)

        if not recipient_ids:
            logger.debug("dispatch: empty audience for type=%s — nothing to write", notif_type_str)
            return

        # ── Step 5: Register on_commit — nothing is written until COMMIT ─────
        # This is the safety net: if the business transaction rolls back
        # (e.g. LC save fails), this callback never fires and zero notification
        # rows are written.
        transaction.on_commit(lambda: cls._write_notifications(
            notif_type          = notif_type_str,
            category            = category_str,
            recipient_ids       = list(recipient_ids),
            rendered            = rendered,
            context             = context,
            entity_type         = resolved_entity_type,
            entity_id           = entity_id,
            actor_id            = actor_id,
            dedupe_key          = dedupe_key,
            redirect_url        = redirect_url,
        ))

        logger.debug(
            "dispatch: registered on_commit for type=%s recipients=%d",
            notif_type_str, len(recipient_ids)
        )

    @classmethod
    def _write_notifications(
        cls,
        notif_type:    str,
        category:      str,
        recipient_ids: list,
        rendered:      dict,
        context:       dict,
        entity_type:   Optional[str],
        entity_id:     Optional[str],
        actor_id:      Optional[str],
        dedupe_key:    Optional[str],
        redirect_url:  Optional[str] = None,
    ) -> None:
        """
        Bulk inserts notification rows after the business transaction has committed.
        Called by on_commit — never call this directly.
        """
        from db.notification import Notification

        system_admin_id = settings.SYSTEM_ADMIN_ID

        rows = [
            Notification(
                id           = uuid.uuid4(),
                user_id      = uid,
                type         = notif_type,
                category     = category,
                title        = rendered["title"],
                description  = rendered["body"],
                context      = context,
                entity_type  = entity_type,
                entity_id    = entity_id,
                actor_id     = actor_id,
                is_read      = False,
                is_archived  = False,
                dedupe_key   = dedupe_key,
                redirect_url = redirect_url,
                created_by_id = system_admin_id,
            )
            for uid in recipient_ids
        ]

        # ignore_conflicts=True: if (user_id, dedupe_key) already exists
        # (e.g. Celery retry or double-click), the row is silently skipped.
        # No exception, no duplicate, no data corruption.
        Notification.objects.bulk_create(
            rows,
            ignore_conflicts=True,
            batch_size=1000,
        )

        # New unread rows landed — the cached unread_count for every
        # recipient is now stale. Bounded to this batch's recipient list,
        # same size class as the bulk_create itself.
        from api.notification.notifications_utils import invalidate_unread_count
        for uid in recipient_ids:
            invalidate_unread_count(uid)

        logger.info(
            "_write_notifications: type=%s attempted=%d",
            notif_type, len(rows)
        )

    @classmethod
    def _write_broadcast(
        cls,
        notif_type:  str,
        category:    str,
        rendered:    dict,
        context:     dict,
        entity_type: Optional[str],
        entity_id:   Optional[str],
        actor_id:    Optional[str],
        dedupe_key:  Optional[str],
        target_type: str,
        target_id:   Optional[str],
        url:         Optional[str] = None,
        expires_at:  Optional[datetime] = None,
    ) -> None:
        """
        Writes exactly one broadcast_notification row for a large audience,
        instead of one notification row per recipient. Called by on_commit —
        never call this directly.
        """
        from db.user import User
        from api.notification.broadcast_utils import BroadcastUtils

        writer_id = actor_id or settings.SYSTEM_ADMIN_ID
        writer = User.objects.filter(id=writer_id).first()
        if not writer:
            logger.error(
                "_write_broadcast: writer user id=%s not found — dropping broadcast for type=%s",
                writer_id, notif_type
            )
            return

        BroadcastUtils.create_broadcast(
            title        = rendered["title"],
            description  = rendered["body"],
            url          = url,
            target_type  = target_type,
            target_id    = target_id,
            created_by   = writer,
            expiry_key   = notif_type.lower(),
            expires_at   = expires_at,
            notif_type   = notif_type,
            category     = category,
            context      = context,
            entity_type  = entity_type,
            entity_id    = entity_id,
            actor        = writer if actor_id else None,
            dedupe_key   = dedupe_key,
        )

        logger.info(
            "_write_broadcast: type=%s target_type=%s target_id=%s",
            notif_type, target_type, target_id
        )


# ─────────────────────────────────────────────────────────────────────────────
# Entity type map — derives entity_type from notif_type automatically
#
# Producers don't need to know which entity type each notification maps to.
# Add entries here as modules are built. If a type is not here and no
# entity_type is passed, entity_type will be NULL in the notification row.
# ─────────────────────────────────────────────────────────────────────────────

_ENTITY_TYPE_MAP: dict[str, str] = {
    # Learning Circle
    NotificationType.LC_JOIN_REQUEST:      "learning_circle",
    NotificationType.LC_JOIN_APPROVED:     "learning_circle",
    NotificationType.LC_JOIN_REJECTED:     "learning_circle",
    NotificationType.LC_MEETING_SCHEDULED: "learning_circle",
    NotificationType.LC_MEMBER_REMOVED:    "learning_circle",
    NotificationType.LC_MEMBER_LEFT:       "learning_circle",
    NotificationType.LC_INVITE:            "learning_circle",

    # Events
    NotificationType.EVENT_PUBLISHED:          "event",
    NotificationType.EVENT_APPROVAL_STAGE:     "event",
    NotificationType.EVENT_REJECTED:           "event",
    NotificationType.EVENT_CO_OWNER_ADDED:     "event",
    NotificationType.EVENT_CO_OWNER_REMOVED:   "event",
    NotificationType.ADMIN_EVENT_PENDING:      "event",
    NotificationType.CAMPUS_EVENT_PENDING:     "event",
    NotificationType.MENTOR_EVENT_PENDING:     "event",
    NotificationType.EVENT_CANCELLED:          "event",
    NotificationType.EVENT_COLLAB_INVITED:     "event",
    NotificationType.EVENT_COLLAB_ACCEPTED:    "event",
    NotificationType.EVENT_COLLAB_REJECTED:    "event",
    NotificationType.EVENT_COLLAB_REMOVED:     "event",

    # Company
    NotificationType.ADMIN_COMPANY_PENDING:                     "company",
    NotificationType.COMPANY_VERIFIED:                          "company",
    NotificationType.COMPANY_REJECTED:                          "company",
    NotificationType.COMPANY_DEACTIVATED:                       "company",
    NotificationType.COMPANY_REACTIVATED:                       "company",
    NotificationType.COMPANY_DELEGATE_INVITED:                  "company_admin_link",
    NotificationType.COMPANY_DELEGATE_REVOKED:                  "company_admin_link",
    NotificationType.COMPANY_DELEGATE_LEFT:                     "company_admin_link",
    NotificationType.MENTOR_NOMINATED:                          "mentor_application",
    NotificationType.COMPANY_MENTOR_APPLICATION_SUBMITTED:      "mentor_application",
    NotificationType.COMPANY_MENTOR_APPLICATION_APPROVED:       "mentor_application",
    NotificationType.COMPANY_MENTOR_APPLICATION_REJECTED:       "mentor_application",

    # Jobs
    NotificationType.JOB_PENDING_APPROVAL: "job",
    NotificationType.JOB_APPROVED:         "job",
    NotificationType.JOB_NEEDS_REVISION:   "job",
    NotificationType.JOB_REJECTED:         "job",
    NotificationType.JOB_APPLICATION_STATUS: "job_application",

    # Karma
    NotificationType.KARMA_AWARDED: "karma_activity_log",
    NotificationType.KARMA_REMOVED: "karma_activity_log",

    # Media Content
    NotificationType.OFFICE_HOURS_ANNOUNCED:          "media_content",
    NotificationType.SALT_MANGO_TREE_ANNOUNCED:       "media_content",
    NotificationType.INSPIRATION_STATION_ANNOUNCED:   "media_content",
    NotificationType.GRAB_YOUR_SUPERPOWERS_ANNOUNCED: "media_content",

    # Add more as modules are built:
    # NotificationType.SESSION_BOOKED:    "session",
}
