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
    LC_MEMBER_LEFT        = "LC_MEMBER_LEFT"
    LC_INVITE            = "LC_INVITE"

    # ── Events ────────────────────────────────────────────────────────────────
    EVENT_PUBLISHED          = "EVENT_PUBLISHED"          # creator: event is now live
    EVENT_APPROVAL_STAGE     = "EVENT_APPROVAL_STAGE"     # creator: approved, moving to next stage
    EVENT_REJECTED           = "EVENT_REJECTED"           # creator: event rejected
    EVENT_CO_OWNER_ADDED     = "EVENT_CO_OWNER_ADDED"     # invited user: added as co-owner
    EVENT_CO_OWNER_REMOVED   = "EVENT_CO_OWNER_REMOVED"   # removed user: removed as co-owner
    ADMIN_EVENT_PENDING      = "ADMIN_EVENT_PENDING"      # admins: new event needs review
    CAMPUS_EVENT_PENDING     = "CAMPUS_EVENT_PENDING"     # campus leads: event needs their review
    MENTOR_EVENT_PENDING     = "MENTOR_EVENT_PENDING"     # mentors/company owner: event needs their review
    EVENT_CANCELLED          = "EVENT_CANCELLED"          # interested users: event was cancelled
    EVENT_COLLAB_INVITED     = "EVENT_COLLAB_INVITED"     # entity lead(s): invited to collaborate
    EVENT_COLLAB_ACCEPTED    = "EVENT_COLLAB_ACCEPTED"    # inviter: collaboration invite accepted
    EVENT_COLLAB_REJECTED    = "EVENT_COLLAB_REJECTED"    # inviter: collaboration invite rejected
    EVENT_COLLAB_REMOVED     = "EVENT_COLLAB_REMOVED"     # entity lead(s): collaboration removed

    # ── Company ───────────────────────────────────────────────────────────────
    ADMIN_COMPANY_PENDING              = "ADMIN_COMPANY_PENDING"              # admins: new company registration needs review
    COMPANY_VERIFIED                   = "COMPANY_VERIFIED"                   # owner: company approved
    COMPANY_REJECTED                   = "COMPANY_REJECTED"                   # owner: company rejected
    COMPANY_DEACTIVATED                = "COMPANY_DEACTIVATED"                # owner (if admin-triggered) + revoked co-admins + admins (audit)
    COMPANY_REACTIVATED                = "COMPANY_REACTIVATED"                # owner: company reactivated
    COMPANY_DELEGATE_INVITED           = "COMPANY_DELEGATE_INVITED"           # invitee: invited as co-admin delegate
    COMPANY_DELEGATE_REVOKED           = "COMPANY_DELEGATE_REVOKED"           # delegate: co-admin access revoked
    COMPANY_DELEGATE_LEFT              = "COMPANY_DELEGATE_LEFT"              # owner: a delegate self-left
    MENTOR_NOMINATED                   = "MENTOR_NOMINATED"                   # nominated user: approved as company mentor immediately
    COMPANY_MENTOR_APPLICATION_SUBMITTED = "COMPANY_MENTOR_APPLICATION_SUBMITTED"  # owner: someone self-applied to mentor
    COMPANY_MENTOR_APPLICATION_APPROVED  = "COMPANY_MENTOR_APPLICATION_APPROVED"   # applicant: self-apply approved
    COMPANY_MENTOR_APPLICATION_REJECTED  = "COMPANY_MENTOR_APPLICATION_REJECTED"   # applicant: self-apply rejected

    # ── Jobs ──────────────────────────────────────────────────────────────────
    JOB_PENDING_APPROVAL    = "JOB_PENDING_APPROVAL"    # owner: a job (new or re-submitted) needs approval
    JOB_APPROVED            = "JOB_APPROVED"            # job creator: approved and now live
    JOB_NEEDS_REVISION      = "JOB_NEEDS_REVISION"      # job creator: sent back with a revision note
    JOB_REJECTED             = "JOB_REJECTED"           # job creator: rejected
    JOB_APPLICATION_STATUS  = "JOB_APPLICATION_STATUS"  # applicant: their application status changed

    # ── Karma ─────────────────────────────────────────────────────────────────
    KARMA_AWARDED = "KARMA_AWARDED"  # recipient: karma points were awarded
    KARMA_REMOVED = "KARMA_REMOVED"  # recipient: karma points were reversed/removed

    # ── Media Content (weekly shows) ────────────────────────────────────────────
    OFFICE_HOURS_ANNOUNCED           = "OFFICE_HOURS_ANNOUNCED"           # tagged IG members: new session
    SALT_MANGO_TREE_ANNOUNCED        = "SALT_MANGO_TREE_ANNOUNCED"        # all users: new episode
    INSPIRATION_STATION_ANNOUNCED    = "INSPIRATION_STATION_ANNOUNCED"    # all users: new episode
    GRAB_YOUR_SUPERPOWERS_ANNOUNCED  = "GRAB_YOUR_SUPERPOWERS_ANNOUNCED"  # all users: new session

    # ── Admin ─────────────────────────────────────────────────────────────────
    ADMIN_BROADCAST = "ADMIN_BROADCAST"  # all users: free-text admin announcement

    # ── Add more modules below as they are built ──────────────────────────────
    # MENTORSHIP, INTERN, TASKS ...


# ─────────────────────────────────────────────────────────────────────────────
# 2. Category — the product module a notification type belongs to
#
# Stored in notification.category column.
# Used by frontend to filter: "show me only LC notifications."
# Never set by a producer — dispatch() derives it from TYPE_META.
# ─────────────────────────────────────────────────────────────────────────────

class Category(str, Enum):
    LC      = "LC"
    EVENTS  = "EVENTS"
    COMPANY = "COMPANY"
    KARMA   = "KARMA"
    JOBS    = "JOBS"
    MEDIA_CONTENT = "MEDIA_CONTENT"
    ADMIN   = "ADMIN"

    # Add below as modules are built:
    # MENTORSHIP     = "MENTORSHIP"
    # INTERN         = "INTERN"
    # TASKS          = "TASKS"


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
    NotificationType.LC_MEMBER_LEFT: TypeMeta(
        category    = Category.LC,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.LC_INVITE: TypeMeta(
        category    = Category.LC,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),

    # ── Events — all personal, all 4 channels ─────────────────────────────────
    NotificationType.EVENT_PUBLISHED: TypeMeta(
        category    = Category.EVENTS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.EVENT_APPROVAL_STAGE: TypeMeta(
        category    = Category.EVENTS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.EVENT_REJECTED: TypeMeta(
        category    = Category.EVENTS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.EVENT_CO_OWNER_ADDED: TypeMeta(
        category    = Category.EVENTS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.ADMIN_EVENT_PENDING: TypeMeta(
        category    = Category.EVENTS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.CAMPUS_EVENT_PENDING: TypeMeta(
        category    = Category.EVENTS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.MENTOR_EVENT_PENDING: TypeMeta(
        category    = Category.EVENTS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.EVENT_CO_OWNER_REMOVED: TypeMeta(
        category    = Category.EVENTS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.EVENT_CANCELLED: TypeMeta(
        category    = Category.EVENTS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.EVENT_COLLAB_INVITED: TypeMeta(
        category    = Category.EVENTS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.EVENT_COLLAB_ACCEPTED: TypeMeta(
        category    = Category.EVENTS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.EVENT_COLLAB_REJECTED: TypeMeta(
        category    = Category.EVENTS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.EVENT_COLLAB_REMOVED: TypeMeta(
        category    = Category.EVENTS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),

    # ── Company — all personal, all 4 channels ────────────────────────────────
    NotificationType.ADMIN_COMPANY_PENDING: TypeMeta(
        category    = Category.COMPANY,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.COMPANY_VERIFIED: TypeMeta(
        category    = Category.COMPANY,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.COMPANY_REJECTED: TypeMeta(
        category    = Category.COMPANY,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.COMPANY_DEACTIVATED: TypeMeta(
        category    = Category.COMPANY,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.COMPANY_REACTIVATED: TypeMeta(
        category    = Category.COMPANY,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.COMPANY_DELEGATE_INVITED: TypeMeta(
        category    = Category.COMPANY,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.COMPANY_DELEGATE_REVOKED: TypeMeta(
        category    = Category.COMPANY,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.COMPANY_DELEGATE_LEFT: TypeMeta(
        category    = Category.COMPANY,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.MENTOR_NOMINATED: TypeMeta(
        category    = Category.COMPANY,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.COMPANY_MENTOR_APPLICATION_SUBMITTED: TypeMeta(
        category    = Category.COMPANY,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.COMPANY_MENTOR_APPLICATION_APPROVED: TypeMeta(
        category    = Category.COMPANY,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.COMPANY_MENTOR_APPLICATION_REJECTED: TypeMeta(
        category    = Category.COMPANY,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),

    # ── Jobs — all personal, all 4 channels ───────────────────────────────────
    NotificationType.JOB_PENDING_APPROVAL: TypeMeta(
        category    = Category.JOBS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.JOB_APPROVED: TypeMeta(
        category    = Category.JOBS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.JOB_NEEDS_REVISION: TypeMeta(
        category    = Category.JOBS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.JOB_REJECTED: TypeMeta(
        category    = Category.JOBS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.JOB_APPLICATION_STATUS: TypeMeta(
        category    = Category.JOBS,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),

    # ── Karma — personal, all 4 channels ───────────────────────────────────────
    NotificationType.KARMA_AWARDED: TypeMeta(
        category    = Category.KARMA,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.KARMA_REMOVED: TypeMeta(
        category    = Category.KARMA,
        is_personal = True,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),

    # ── Media Content — topical announcements, not personal ────────────────────
    NotificationType.OFFICE_HOURS_ANNOUNCED: TypeMeta(
        category    = Category.MEDIA_CONTENT,
        is_personal = False,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.SALT_MANGO_TREE_ANNOUNCED: TypeMeta(
        category    = Category.MEDIA_CONTENT,
        is_personal = False,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.INSPIRATION_STATION_ANNOUNCED: TypeMeta(
        category    = Category.MEDIA_CONTENT,
        is_personal = False,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),
    NotificationType.GRAB_YOUR_SUPERPOWERS_ANNOUNCED: TypeMeta(
        category    = Category.MEDIA_CONTENT,
        is_personal = False,
        eligible    = ["IN_APP", "WEBSOCKET", "PUSH", "EMAIL"],
    ),

    # ── Admin — free-text, not personal, no PUSH/EMAIL yet ────────────────────
    NotificationType.ADMIN_BROADCAST: TypeMeta(
        category    = Category.ADMIN,
        is_personal = False,
        eligible    = ["IN_APP", "WEBSOCKET"],
    ),

}
# fmt: on
