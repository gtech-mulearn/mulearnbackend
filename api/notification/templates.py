import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Template Registry
#
# Maps (notification_type, render_target) → {title, body} string templates.
# {placeholders} are filled from the context dict the producer passes.
#
# render_target values:
#   "IN_APP"    → text shown in the notification bell / feed
#   "WEBSOCKET" → same as IN_APP for now (same text, different delivery)
#   "PUSH"      → added in Phase 2 (shorter, fits notification tray)
#   "EMAIL"     → added in Phase 3 (longer, can be HTML)
#
# Only LC + IN_APP/WEBSOCKET targets are defined here.
# Add more (type, target) pairs as modules and channels are built.
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATES: dict[tuple, dict] = {

    # ── LC_JOIN_REQUEST ───────────────────────────────────────────────────────
    # Who gets it: LC lead
    # Context keys: lc_name, requester_name
    ("LC_JOIN_REQUEST", "IN_APP"): {
        "title": "New Join Request",
        "body":  "{requester_name} wants to join {lc_name}.",
    },

    # ── LC_JOIN_APPROVED ──────────────────────────────────────────────────────
    # Who gets it: the requester
    # Context keys: lc_name
    ("LC_JOIN_APPROVED", "IN_APP"): {
        "title": "Join Request Approved!",
        "body":  "Your request to join {lc_name} has been approved.",
    },

    # ── LC_JOIN_REJECTED ──────────────────────────────────────────────────────
    # Who gets it: the requester
    # Context keys: lc_name
    ("LC_JOIN_REJECTED", "IN_APP"): {
        "title": "Join Request Rejected",
        "body":  "Your request to join {lc_name} was not approved.",
    },

    # ── LC_MEETING_SCHEDULED ──────────────────────────────────────────────────
    # Who gets it: all accepted members except the meeting creator
    # Context keys: lc_name, meet_time
    ("LC_MEETING_SCHEDULED", "IN_APP"): {
        "title": "New Meeting Scheduled",
        "body":  "A new meeting for {lc_name} has been scheduled on {meet_time}.",
    },

    # ── LC_MEMBER_REMOVED ─────────────────────────────────────────────────────
    # Who gets it: the removed member
    # Context keys: lc_name
    ("LC_MEMBER_REMOVED", "IN_APP"): {
        "title": "Removed from Circle",
        "body":  "You have been removed from {lc_name}.",
    },

    # ── LC_INVITE ─────────────────────────────────────────────────────────────
    # Who gets it: the invited user
    # Context keys: lc_name
    ("LC_INVITE", "IN_APP"): {
        "title": "Circle Invitation",
        "body":  "You have been invited to join {lc_name}.",
    },

}

# Copy all IN_APP entries to WEBSOCKET automatically.
# WebSocket uses the same title/body as IN_APP — it's just a different delivery pipe.
# When PUSH and EMAIL templates differ (Phase 2/3), add them manually above.
for (_type, _target), _tmpl in list(TEMPLATES.items()):
    if _target == "IN_APP":
        TEMPLATES[(_type, "WEBSOCKET")] = _tmpl


# ─────────────────────────────────────────────────────────────────────────────
# render_template(notif_type, target, context) → {title, body} or None
#
# Called by dispatch() to get the rendered title and body.
# Returns None if:
#   - no template registered for this (type, target) pair  → SKIPPED: NO_TEMPLATE
#   - context is missing a required placeholder key        → SKIPPED: TEMPLATE_ERROR
# ─────────────────────────────────────────────────────────────────────────────

def render_template(notif_type: str, target: str, context: dict) -> dict | None:
    """
    Renders the title and body for a given (type, target) using context variables.

    Args:
        notif_type: NotificationType value e.g. "LC_JOIN_APPROVED"
        target:     Render target e.g. "IN_APP", "WEBSOCKET", "PUSH", "EMAIL"
        context:    Dict of variables from the producer e.g. {"lc_name": "Web Dev"}

    Returns:
        {"title": "...", "body": "..."} on success
        None if no template found or context key is missing
    """
    template = TEMPLATES.get((notif_type, target))
    if not template:
        return None

    try:
        return {
            "title": template["title"].format(**context),
            "body":  template["body"].format(**context),
        }
    except KeyError as missing_key:
        logger.warning(
            "render_template: missing context key %s for type=%s target=%s context=%s",
            missing_key, notif_type, target, context,
        )
        return None
