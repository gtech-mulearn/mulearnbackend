from datetime import datetime, timedelta
from typing import Optional

from db.notification import BroadcastNotification
from utils.utils import DateTimeUtils


# Expiry windows as specified in the implementation doc
EXPIRY_DAYS = {
    'event_published':   7,
    'event_cancelled':   3,
    'collab_response':   5,
    'lc_created':        7,
}


class BroadcastUtils:
    """
    Utility class for creating BroadcastNotification records.

    A single row is written per broadcast event — recipients are resolved
    dynamically at read time based on target_type + target_id.

    target_type reference:
        'campus'          -> all users in that campus org (target_id = org_id)
        'interest_group'  -> all active learner members of that IG (target_id = ig_id)
        'campus_ig'       -> all learners in a campus-IG chapter (target_id = campus_ig_composite_id)
        'event_interest'  -> all users who expressed interest in the event (target_id = event_id)
        'event_coowners'  -> event creator + co-owners (target_id = event_id)
        'global'          -> all active users (target_id = None)
    """

    @staticmethod
    def create_broadcast(
        title: str,
        description: str,
        target_type: str,
        created_by,
        expiry_key: str,
        url: str = None,
        target_id: str = None,
        notif_type: str = None,
        category: str = None,
        context: dict = None,
        entity_type: str = None,
        entity_id: str = None,
        actor=None,
        dedupe_key: str = None,
        expires_at: Optional[datetime] = None,
    ) -> BroadcastNotification:
        """
        Create and persist a single BroadcastNotification row.

        Args:
            title:       Short headline.
            description: Body text.
            target_type: Audience category — see class docstring.
            created_by:  User instance that triggered the action (writing account).
            expiry_key:  One of the keys in EXPIRY_DAYS.
            url:         Deep-link URL (optional).
            target_id:   ID of the target entity (None for 'global').
            notif_type:  NotificationType value, mirrors Notification.type — lets a
                         merged read-query select the same columns from both tables.
            category:    Product module (e.g. "EVENTS"). Defaults to "SYSTEM"
                         (the DB column default) when not given.
            context:     Raw producer variables, for future re-render without a
                         schema change — mirrors Notification.context.
            entity_type/entity_id: What this broadcast is ABOUT, for deep-linking
                         — distinct from target_type/target_id (who the AUDIENCE is).
            actor:       User who triggered this broadcast. Defaults to created_by
                         when not given — for existing callers, the writing account
                         and the triggering actor are the same.
            dedupe_key:  Idempotency key ("type:entity_id:occurrence"). When given,
                         a retry/double-click with the same key returns the existing
                         row instead of inserting a duplicate.
            expires_at:  Explicit expiry, overriding the expiry_key/EXPIRY_DAYS lookup —
                         used by admin broadcasts, which choose their own window per send.

        Returns:
            The created (or, if dedupe_key already exists, the existing)
            BroadcastNotification instance.
        """
        now = DateTimeUtils.get_current_utc_time()
        if expires_at is None:
            expiry_days = EXPIRY_DAYS.get(expiry_key, 7)
            expires_at  = now + timedelta(days=expiry_days)

        fields = dict(
            title=title,
            description=description,
            url=url,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            created_by=created_by,
            created_at=now,
            expires_at=expires_at,
            notif_type=notif_type,
            category=category or "SYSTEM",
            context=context,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor or created_by,
        )

        if dedupe_key:
            # get_or_create on the unique index (uq_broadcast_dedupe): a retry
            # or double-click with the same key returns the row already
            # written instead of raising an IntegrityError or duplicating it.
            broadcast, _ = BroadcastNotification.objects.get_or_create(
                dedupe_key=dedupe_key,
                defaults=fields,
            )
            return broadcast

        return BroadcastNotification.objects.create(dedupe_key=dedupe_key, **fields)
