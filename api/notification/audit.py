"""Writer for the team activity log (SystemActionLog) shared by the
announcement and push admin endpoints.

Callers must use ``from api.notification import audit`` and ``audit.record(...)``
so the function can be patched in tests.
"""
from dataclasses import dataclass

from db.mentor import SystemActionLog
from db.notification import BroadcastNotification
from utils.permission import verified_role_titles
from utils.types import TEAM_ROLES

ACTION_LABELS: dict[str, str] = {
    "NOTIF_BROADCAST_CREATE": "Created announcement",
    "NOTIF_BROADCAST_SEND": "Sent announcement to everyone",
    "NOTIF_BROADCAST_UPDATE": "Edited announcement",
    "NOTIF_BROADCAST_DELETE": "Deleted announcement",
    "NOTIF_BROADCAST_DEL_ALL": "Deleted all announcements",
    "PUSH_CAMPAIGN_CREATE": "Created push campaign",
    "PUSH_CAMPAIGN_SEND": "Sent push campaign",
    "PUSH_CAMPAIGN_CANCEL": "Cancelled push campaign",
    "PUSH_TEST_SEND": "Sent test push",
    "PUSH_CONFIG_UPDATE": "Changed push settings",
}

DELETE_ALL_ITEM_CAP = 500
REMARKS_MAX = 500


@dataclass(frozen=True)
class AuditSpec:
    action: str
    actor_id: str
    new_data: dict | None = None
    old_data: dict | None = None
    audience_size: int | None = None
    audience_label: str | None = None
    # The subject's name (campaign or announcement title), for rows whose
    # old_data/new_data carry no title of their own (send, cancel, an edit
    # that kept the title).
    title: str | None = None


def team_roles_of(user_id: str) -> list[str]:
    """Verified team roles the user holds, in TEAM_ROLES order."""
    held = verified_role_titles(user_id)
    return [role for role in TEAM_ROLES if role in held]


def record(
    spec: AuditSpec, *, entity_name: str, entity_id: str, note: str | None = None
) -> SystemActionLog:
    roles = team_roles_of(spec.actor_id)
    new_data = {
        **(spec.new_data or {}),
        "_audit": {
            "roles": roles,
            "audience_size": spec.audience_size,
            "audience_label": spec.audience_label,
            "title": spec.title,
        },
    }
    parts = []
    if roles:
        parts.append(" + ".join(roles))
    if spec.audience_size is not None:
        parts.append(f"{spec.audience_size:,} people")
    elif spec.audience_label:
        parts.append(spec.audience_label)
    if note:
        parts.append(note)
    return SystemActionLog.objects.create(
        action_type=spec.action,
        actor_user_id=spec.actor_id,
        entity_name=entity_name,
        entity_id=str(entity_id),
        old_data=spec.old_data,
        new_data=new_data,
        remarks=" · ".join(parts)[:REMARKS_MAX],
    )


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


def snapshot_broadcast(b: BroadcastNotification) -> dict:
    return {
        "id": str(b.id),
        "title": b.title,
        "description": b.description,
        "url": b.url,
        "target_type": b.target_type,
        "target_id": b.target_id,
        "notif_type": b.notif_type,
        "created_by_id": str(b.created_by_id) if b.created_by_id else None,
        "created_at": _iso(b.created_at),
        "expires_at": _iso(b.expires_at),
    }
