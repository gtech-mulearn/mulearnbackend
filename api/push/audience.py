"""
Campaign audiences, paged in chunks over users who have an active push
device (users without one can't receive a push, so they are never loaded).

audience = {"type": "all" | "roles" | "igs" | "colleges" | "muids", "ids": [...]}
  roles     role titles, e.g. ["Student", "Mentor"] (verified links only)
  igs       interest group ids
  colleges  organization ids (verified links only)
  muids     explicit list, e.g. for a pilot group (max 5000)

Keyset pagination on user_id: each call reads one chunk after `after`, so a
campaign to every user never holds the whole user base in memory or in one
query.
"""
from typing import Optional

VALID_TYPES = {"all", "roles", "igs", "colleges", "muids"}
MAX_MUIDS = 5000


class AudienceError(ValueError):
    pass


def validate(audience: dict) -> dict:
    if not isinstance(audience, dict):
        raise AudienceError("audience must be an object")
    kind = audience.get("type")
    if kind not in VALID_TYPES:
        raise AudienceError(f"audience.type must be one of {sorted(VALID_TYPES)}")
    ids = audience.get("ids") or []
    if kind != "all":
        if not isinstance(ids, list) or not ids or not all(isinstance(i, str) and i for i in ids):
            raise AudienceError("audience.ids must be a non-empty list of strings")
        if kind == "muids" and len(ids) > MAX_MUIDS:
            raise AudienceError(f"at most {MAX_MUIDS} muids")
    return {"type": kind, "ids": [] if kind == "all" else list(dict.fromkeys(ids))}


def _base_user_ids():
    from db.push import UserPushDevice

    return UserPushDevice.objects.filter(is_active=True).values_list("user_id", flat=True)


def _filtered(audience: dict):
    from db.organization import UserOrganizationLink
    from db.task import UserIgLink
    from db.user import User, UserRoleLink

    qs = _base_user_ids()
    kind, ids = audience["type"], audience["ids"]
    if kind == "roles":
        qs = qs.filter(user_id__in=UserRoleLink.objects.filter(
            role__title__in=ids, verified=True).values("user_id"))
    elif kind == "igs":
        qs = qs.filter(user_id__in=UserIgLink.objects.filter(ig_id__in=ids).values("user_id"))
    elif kind == "colleges":
        qs = qs.filter(user_id__in=UserOrganizationLink.objects.filter(
            org_id__in=ids, verified=True).values("user_id"))
    elif kind == "muids":
        qs = qs.filter(user_id__in=User.objects.filter(muid__in=ids).values("id"))
    return qs


def next_chunk(audience: dict, after: Optional[str], size: int) -> list:
    """Up to `size` distinct user ids greater than `after`, in order."""
    qs = _filtered(audience)
    if after:
        qs = qs.filter(user_id__gt=after)
    return list(qs.order_by("user_id").distinct()[:size])


def count(audience: dict) -> int:
    return _filtered(audience).distinct().count()
