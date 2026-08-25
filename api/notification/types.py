from dataclasses import dataclass
from enum import Enum
from typing import List


# ─────────────────────────────────────────────────────────────────────────────
# 1. NotificationType — string constants for every notification event
#
# Use these instead of raw strings in producers:
#   ✅  NotificationType.LC_JOIN_APPROVED
#   ❌  "LC_JOIN_APPROVED"   ← typos cause silent failures
#
# Only LC types are defined now. Add other modules here as they are built.
# ─────────────────────────────────────────────────────────────────────────────

class NotificationType(str, Enum):
    # ── Learning Circle ───────────────────────────────────────────────────────
    LC_JOIN_REQUEST      = "LC_JOIN_REQUEST"
    LC_JOIN_APPROVED     = "LC_JOIN_APPROVED"
    LC_JOIN_REJECTED     = "LC_JOIN_REJECTED"
    LC_MEETING_SCHEDULED = "LC_MEETING_SCHEDULED"
    LC_MEMBER_REMOVED    = "LC_MEMBER_REMOVED"
    LC_INVITE            = "LC_INVITE"

    # ── Add more modules below as they are built ──────────────────────────────
    # MENTORSHIP, EVENTS, JOBS, INTERN, TASKS, ADMIN_BROADCAST ...


# ─────────────────────────────────────────────────────────────────────────────
# 2. Category — the product module a notification type belongs to
#
# Stored in notification.category column.
# Used by frontend to filter: "show me only LC notifications."
# Never set by a producer — dispatch() derives it from TYPE_META.
# ─────────────────────────────────────────────────────────────────────────────

class Category(str, Enum):
    LC = "LC"

    # Add below as modules are built:
    # MENTORSHIP     = "MENTORSHIP"
    # EVENTS         = "EVENTS"
    # JOBS           = "JOBS"
    # COMPANY        = "COMPANY"
    # INTERN         = "INTERN"
    # TASKS          = "TASKS"
    # ADMIN          = "ADMIN"
    # ADMIN_BROADCAST = "ADMIN_BROADCAST"


# ─────────────────────────────────────────────────────────────────────────────
# 3. TypeMeta — the rules for each notification type
#
# category:    which Category this type belongs to
# is_personal: True = this type is about ONE user's private data
#              → structurally barred from Discord, even if a policy row exists
# eligible:    which channels this type is ALLOWED to use
#              (channel_policy and user settings can further restrict this,
#               but they cannot ADD channels that are not in this list)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TypeMeta:
    category:    str
    is_personal: bool
    eligible:    List[str]


# ─────────────────────────────────────────────────────────────────────────────
# 4. TYPE_META — the lookup table dispatch() reads per notification type
#
# dispatch() does:
#     meta = TYPE_META.get(notif_type)
#     meta.category    → stored in notification.category
#     meta.is_personal → gates Discord permanently
#     meta.eligible    → passed to channel gate
#
# Adding a new module = adding entries here. Zero changes to dispatch().
# ─────────────────────────────────────────────────────────────────────────────

# fmt: off
TYPE_META: dict[str, TypeMeta] = {

    # ── Learning Circle — all personal, all 4 channels ────────────────────────
    NotificationType.LC_JOIN_REQUEST: TypeMeta(
        category    = Category.LC,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.LC_JOIN_APPROVED: TypeMeta(
        category    = Category.LC,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.LC_JOIN_REJECTED: TypeMeta(
        category    = Category.LC,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.LC_MEETING_SCHEDULED: TypeMeta(
        category    = Category.LC,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.LC_MEMBER_REMOVED: TypeMeta(
        category    = Category.LC,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.LC_INVITE: TypeMeta(
        category    = Category.LC,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),

}
# fmt: on
