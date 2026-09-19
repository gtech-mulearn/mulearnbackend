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

    # ── LC_MEMBER_LEFT ────────────────────────────────────────────────────────
    # Who gets it: the circle lead(s)
    # Context keys: lc_name, member_name
    ("LC_MEMBER_LEFT", "IN_APP"): {
        "title": "Member Left Circle",
        "body":  "{member_name} has left {lc_name}.",
    },

    # ── LC_INVITE ─────────────────────────────────────────────────────────────
    # Who gets it: the invited user
    # Context keys: lc_name
    ("LC_INVITE", "IN_APP"): {
        "title": "Circle Invitation",
        "body":  "You have been invited to join {lc_name}.",
    },

    # ── EVENT_PUBLISHED ───────────────────────────────────────────────────────
    # Who gets it: the event creator
    # Context keys: event_title
    ("EVENT_PUBLISHED", "IN_APP"): {
        "title": "Event Published!",
        "body":  "Your event \"{event_title}\" is now live.",
    },

    # ── EVENT_APPROVAL_STAGE ──────────────────────────────────────────────────
    # Who gets it: the event creator (when approved but not yet published)
    # Context keys: event_title, approver_role
    ("EVENT_APPROVAL_STAGE", "IN_APP"): {
        "title": "Event Approved",
        "body":  "Your event \"{event_title}\" has been approved by the {approver_role} and is progressing through review.",
    },

    # ── EVENT_REJECTED ────────────────────────────────────────────────────────
    # Who gets it: the event creator
    # Context keys: event_title, approver_role, reason
    ("EVENT_REJECTED", "IN_APP"): {
        "title": "Event Rejected",
        "body":  "Your event \"{event_title}\" was rejected by the {approver_role}. Reason: {reason}",
    },

    # ── EVENT_CO_OWNER_ADDED ──────────────────────────────────────────────────
    # Who gets it: the user being added as co-owner
    # Context keys: event_title
    ("EVENT_CO_OWNER_ADDED", "IN_APP"): {
        "title": "Added as Co-Owner",
        "body":  "You have been added as a co-owner of \"{event_title}\".",
    },

    # ── ADMIN_EVENT_PENDING ───────────────────────────────────────────────────
    # Who gets it: the admin who needs to review
    # Context keys: event_title, organiser_name
    ("ADMIN_EVENT_PENDING", "IN_APP"): {
        "title": "Event Awaiting Review",
        "body":  "\"{event_title}\" by {organiser_name} is pending your approval.",
    },

    # ── CAMPUS_EVENT_PENDING ──────────────────────────────────────────────────
    # Who gets it: the campus leads who can approve at this stage
    # Context keys: event_title, organiser_name
    ("CAMPUS_EVENT_PENDING", "IN_APP"): {
        "title": "Event Awaiting Review",
        "body":  "\"{event_title}\" by {organiser_name} is pending your campus approval.",
    },

    # ── MENTOR_EVENT_PENDING ──────────────────────────────────────────────────
    # Who gets it: the mentor(s)/company owner who can approve at this stage
    # Context keys: event_title, organiser_name
    ("MENTOR_EVENT_PENDING", "IN_APP"): {
        "title": "Event Awaiting Review",
        "body":  "\"{event_title}\" by {organiser_name} is pending your approval.",
    },

    # ── EVENT_CO_OWNER_REMOVED ────────────────────────────────────────────────
    # Who gets it: the user removed as co-owner
    # Context keys: event_title
    ("EVENT_CO_OWNER_REMOVED", "IN_APP"): {
        "title": "Removed as Co-Owner",
        "body":  "You have been removed as a co-owner of \"{event_title}\".",
    },

    # ── EVENT_CANCELLED ───────────────────────────────────────────────────────
    # Who gets it: everyone who expressed interest in the event
    # Context keys: event_title
    ("EVENT_CANCELLED", "IN_APP"): {
        "title": "Event Cancelled",
        "body":  "The event \"{event_title}\" has been cancelled.",
    },

    # ── EVENT_COLLAB_INVITED ──────────────────────────────────────────────────
    # Who gets it: the lead(s) of the invited entity (IG/campus/company)
    # Context keys: event_title, entity_name
    ("EVENT_COLLAB_INVITED", "IN_APP"): {
        "title": "Collaboration Invite",
        "body":  "{entity_name} has been invited to collaborate on \"{event_title}\".",
    },

    # ── EVENT_COLLAB_ACCEPTED ─────────────────────────────────────────────────
    # Who gets it: the inviter (event manager)
    # Context keys: event_title, entity_name
    ("EVENT_COLLAB_ACCEPTED", "IN_APP"): {
        "title": "Collaboration Accepted",
        "body":  "{entity_name} accepted the collaboration invite for \"{event_title}\".",
    },

    # ── EVENT_COLLAB_REJECTED ─────────────────────────────────────────────────
    # Who gets it: the inviter (event manager)
    # Context keys: event_title, entity_name, reason
    ("EVENT_COLLAB_REJECTED", "IN_APP"): {
        "title": "Collaboration Rejected",
        "body":  "{entity_name} declined the collaboration invite for \"{event_title}\". Reason: {reason}",
    },

    # ── EVENT_COLLAB_REMOVED ──────────────────────────────────────────────────
    # Who gets it: the lead(s) of the removed entity
    # Context keys: event_title, entity_name
    ("EVENT_COLLAB_REMOVED", "IN_APP"): {
        "title": "Collaboration Removed",
        "body":  "{entity_name}'s collaboration on \"{event_title}\" has been removed.",
    },

    # ── ADMIN_COMPANY_PENDING ─────────────────────────────────────────────────
    # Who gets it: admins
    # Context keys: company_name
    ("ADMIN_COMPANY_PENDING", "IN_APP"): {
        "title": "Company Registration Pending",
        "body":  "\"{company_name}\" has registered and is awaiting your review.",
    },

    # ── COMPANY_VERIFIED ──────────────────────────────────────────────────────
    # Who gets it: the company owner
    # Context keys: company_name
    ("COMPANY_VERIFIED", "IN_APP"): {
        "title": "Company Verified",
        "body":  "\"{company_name}\" has been verified.",
    },

    # ── COMPANY_REJECTED ──────────────────────────────────────────────────────
    # Who gets it: the company owner
    # Context keys: company_name
    ("COMPANY_REJECTED", "IN_APP"): {
        "title": "Company Registration Rejected",
        "body":  "\"{company_name}\"'s registration was rejected.",
    },

    # ── COMPANY_DEACTIVATED ───────────────────────────────────────────────────
    # Who gets it: owner (if admin-triggered), revoked co-admins, admins (audit)
    # Context keys: company_name
    ("COMPANY_DEACTIVATED", "IN_APP"): {
        "title": "Company Deactivated",
        "body":  "\"{company_name}\" has been deactivated.",
    },

    # ── COMPANY_REACTIVATED ───────────────────────────────────────────────────
    # Who gets it: the company owner
    # Context keys: company_name
    ("COMPANY_REACTIVATED", "IN_APP"): {
        "title": "Company Reactivated",
        "body":  "\"{company_name}\" has been reactivated.",
    },

    # ── COMPANY_DELEGATE_INVITED ──────────────────────────────────────────────
    # Who gets it: the invited delegate
    # Context keys: company_name, inviter_name
    ("COMPANY_DELEGATE_INVITED", "IN_APP"): {
        "title": "Company Delegate Invitation",
        "body":  "{inviter_name} has invited you to be an approval delegate for {company_name}.",
    },

    # ── COMPANY_DELEGATE_REVOKED ──────────────────────────────────────────────
    # Who gets it: the revoked delegate
    # Context keys: company_name
    ("COMPANY_DELEGATE_REVOKED", "IN_APP"): {
        "title": "Company Delegate Access Revoked",
        "body":  "Your approval delegate access for {company_name} has been revoked.",
    },

    # ── COMPANY_DELEGATE_LEFT ─────────────────────────────────────────────────
    # Who gets it: the company owner
    # Context keys: company_name, delegate_name
    ("COMPANY_DELEGATE_LEFT", "IN_APP"): {
        "title": "Company Delegate Left",
        "body":  "{delegate_name} has left as an approval delegate for {company_name}.",
    },

    # ── MENTOR_NOMINATED ──────────────────────────────────────────────────────
    # Who gets it: the nominated user
    # Context keys: company_name
    ("MENTOR_NOMINATED", "IN_APP"): {
        "title": "Company Mentor Approved",
        "body":  "You have been approved as a Company Mentor for {company_name}.",
    },

    # ── COMPANY_MENTOR_APPLICATION_SUBMITTED ──────────────────────────────────
    # Who gets it: the company owner
    # Context keys: applicant_name, company_name
    ("COMPANY_MENTOR_APPLICATION_SUBMITTED", "IN_APP"): {
        "title": "New Mentor Application",
        "body":  "{applicant_name} has applied to be a mentor for {company_name}.",
    },

    # ── COMPANY_MENTOR_APPLICATION_APPROVED ───────────────────────────────────
    # Who gets it: the applicant
    # Context keys: company_name
    ("COMPANY_MENTOR_APPLICATION_APPROVED", "IN_APP"): {
        "title": "Mentor Application Approved",
        "body":  "Your application to be a mentor for {company_name} has been approved.",
    },

    # ── COMPANY_MENTOR_APPLICATION_REJECTED ───────────────────────────────────
    # Who gets it: the applicant
    # Context keys: company_name
    ("COMPANY_MENTOR_APPLICATION_REJECTED", "IN_APP"): {
        "title": "Mentor Application Rejected",
        "body":  "Your application to be a mentor for {company_name} was not approved.",
    },

    # ── JOB_PENDING_APPROVAL ──────────────────────────────────────────────────
    # Who gets it: the company owner
    # Context keys: job_title
    ("JOB_PENDING_APPROVAL", "IN_APP"): {
        "title": "Job Posting Awaiting Approval",
        "body":  "A job \"{job_title}\" is awaiting your approval.",
    },

    # ── JOB_APPROVED ──────────────────────────────────────────────────────────
    # Who gets it: the job's creator
    # Context keys: job_title
    ("JOB_APPROVED", "IN_APP"): {
        "title": "Job Posting Approved",
        "body":  "Your job posting \"{job_title}\" has been approved and is now live.",
    },

    # ── JOB_NEEDS_REVISION ────────────────────────────────────────────────────
    # Who gets it: the job's creator
    # Context keys: job_title, note
    ("JOB_NEEDS_REVISION", "IN_APP"): {
        "title": "Job Posting Needs Revision",
        "body":  "Your job \"{job_title}\" needs changes: {note}",
    },

    # ── JOB_REJECTED ──────────────────────────────────────────────────────────
    # Who gets it: the job's creator
    # Context keys: job_title, reason
    ("JOB_REJECTED", "IN_APP"): {
        "title": "Job Posting Rejected",
        "body":  "Your job posting \"{job_title}\" was rejected. Reason: {reason}",
    },

    # ── JOB_APPLICATION_STATUS ────────────────────────────────────────────────
    # Who gets it: the applicant
    # Context keys: job_title, status
    ("JOB_APPLICATION_STATUS", "IN_APP"): {
        "title": "Application Status Updated",
        "body":  "Your application for \"{job_title}\" is now {status}.",
    },

    # ── KARMA_AWARDED ─────────────────────────────────────────────────────────
    # Who gets it: the user who earned it
    # Context keys: karma, reason
    ("KARMA_AWARDED", "IN_APP"): {
        "title": "Karma Awarded",
        "body":  "You earned {karma} karma for {reason}.",
    },

    # ── KARMA_REMOVED ─────────────────────────────────────────────────────────
    # Who gets it: the affected user
    # Context keys: karma, reason
    ("KARMA_REMOVED", "IN_APP"): {
        "title": "Karma Removed",
        "body":  "{karma} karma was removed for {reason}.",
    },

    # ── OFFICE_HOURS_ANNOUNCED ────────────────────────────────────────────────
    # Who gets it: members of the tagged Interest Group(s)
    # Context keys: title, performer
    ("OFFICE_HOURS_ANNOUNCED", "IN_APP"): {
        "title": "New Office Hours",
        "body":  "New Office Hours: \"{title}\" with {performer}.",
    },

    # ── SALT_MANGO_TREE_ANNOUNCED ─────────────────────────────────────────────
    # Who gets it: all active users
    # Context keys: title, campus
    ("SALT_MANGO_TREE_ANNOUNCED", "IN_APP"): {
        "title": "New Salt Mango Tree Episode",
        "body":  "New Salt Mango Tree episode: \"{title}\", hosted at {campus}.",
    },

    # ── INSPIRATION_STATION_ANNOUNCED ─────────────────────────────────────────
    # Who gets it: all active users
    # Context keys: title, campus
    ("INSPIRATION_STATION_ANNOUNCED", "IN_APP"): {
        "title": "New Inspiration Station Radio Episode",
        "body":  "New Inspiration Station Radio episode: \"{title}\", hosted at {campus}.",
    },

    # ── GRAB_YOUR_SUPERPOWERS_ANNOUNCED ───────────────────────────────────────
    # Who gets it: all active users
    # Context keys: title, campus, performer
    ("GRAB_YOUR_SUPERPOWERS_ANNOUNCED", "IN_APP"): {
        "title": "New Grab Your Superpowers Session",
        "body":  "New Grab Your Superpowers session: \"{title}\" with {performer} at {campus}.",
    },

    # ── ADMIN_BROADCAST ───────────────────────────────────────────────────────
    # Who gets it: all active users
    # Context keys: title, body — passed through verbatim, composed by the admin
    # at send time rather than fixed at registration time like every other type.
    ("ADMIN_BROADCAST", "IN_APP"): {
        "title": "{title}",
        "body":  "{body}",
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
