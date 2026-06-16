from datetime import timedelta

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
    ) -> BroadcastNotification:
        """
        Create and persist a single BroadcastNotification row.

        Args:
            title:       Short headline (max 50 chars).
            description: Body text (max 200 chars).
            target_type: Audience category — see class docstring.
            created_by:  User instance that triggered the action.
            expiry_key:  One of the keys in EXPIRY_DAYS.
            url:         Deep-link URL (optional).
            target_id:   ID of the target entity (None for 'global').

        Returns:
            The created BroadcastNotification instance.
        """
        now        = DateTimeUtils.get_current_utc_time()
        expiry_days = EXPIRY_DAYS.get(expiry_key, 7)
        expires_at = now + timedelta(days=expiry_days)

        return BroadcastNotification.objects.create(
            title=title,
            description=description,
            url=url,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            created_by=created_by,
            created_at=now,
            expires_at=expires_at,
        )
