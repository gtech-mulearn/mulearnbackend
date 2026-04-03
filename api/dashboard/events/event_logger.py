"""
event_logger.py — Centralized audit-log helper for Events.

All views should call `log_event_action()` instead of creating EventLog
rows directly.  This keeps the log format consistent and in one place.

Stored structure inside EventLog.changed_fields (a JSONField):
{
    "action":  "<EventLog.Action constant>",
    "changes": {                              # only for field-level edits
        "Human Field Label": {"from": ..., "to": ...},
        ...
    },
    "details": {                             # for connection events & misc
        "<key>": <value>,
        ...
    }
}
"""

import uuid

from db.events import EventLog


# ─────────────────────────────────────────────────────────────────────────────
# Human-readable labels for raw Event field names
# ─────────────────────────────────────────────────────────────────────────────

FIELD_LABELS = {
    'title':                'Title',
    'description':          'Description',
    'cover_image':          'Cover Image',
    'banner_image':         'Banner Image',
    'category':             'Category',
    'category_id':          'Category',
    'start_datetime':       'Start Date & Time',
    'end_datetime':         'End Date & Time',
    'registration_url':     'Registration URL',
    'registration_deadline':'Registration Deadline',
    'min_karma':            'Minimum Karma',
    'venue_type':           'Venue Type',
    'venue_address':        'Venue Address',
    'venue_city':           'Venue City',
    'venue_maps_url':       'Venue Maps URL',
    'venue_online_link':    'Online Link',
    'venue_platform':       'Online Platform',
    'scope':                'Event Scope',
    'scope_org':            'Scope Campus / Company',
    'scope_org_id':         'Scope Campus / Company',
    'scope_ig':             'Scope Interest Group',
    'scope_ig_id':          'Scope Interest Group',
    'scope_ci_id':          'Scope Campus-IG',
    'organiser_type':       'Organiser Type',
    'organiser_ig':         'Organiser IG',
    'organiser_ig_id':      'Organiser IG',
    'organiser_org':        'Organiser Campus / Company',
    'organiser_org_id':     'Organiser Campus / Company',
    'organiser_ci_id':      'Organiser Campus-IG',
    'is_collaboration':     'Collaboration Event',
    'is_featured':          'Featured',
    'tags':                 'Tags',
    'user_limit':           'User Limit',
    'status':               'Status',
    'deleted_at':           'Cancelled At',
}


def _serialize_value(value):
    """Convert a value to something JSON-safe and human-readable."""
    if value is None:
        return None
    # Django model instance — extract PK + str representation
    if hasattr(value, 'pk') and hasattr(value, '__str__'):
        return {'id': str(value.pk), 'name': str(value)}
    # Datetime
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


# ─────────────────────────────────────────────────────────────────────────────
# Public helpers
# ─────────────────────────────────────────────────────────────────────────────

def build_diff(instance, validated_data):
    """
    Compare `validated_data` (incoming) against the current `instance` values
    and return a dict of *only the fields that actually changed*, using
    human-readable labels.

    Call this BEFORE saving the instance.

    Returns:
        {
          "Title":       {"from": "Old Title",  "to": "New Title"},
          "Venue City":  {"from": "Kochi",      "to": "Thrissur"},
          ...
        }
    """
    changes = {}
    for field, new_value in validated_data.items():
        label = FIELD_LABELS.get(field, field.replace('_', ' ').title())

        # Resolve the current value on the instance
        try:
            old_value = getattr(instance, field)
        except AttributeError:
            old_value = None

        serialized_old = _serialize_value(old_value)
        serialized_new = _serialize_value(new_value)

        # Only record genuinely changed fields
        if serialized_old != serialized_new:
            changes[label] = {'from': serialized_old, 'to': serialized_new}

    return changes


def log_event_action(event, user_id, action, changes=None, details=None):
    """
    Create an EventLog row with a structured `changed_fields` payload.

    Args:
        event    — Event instance
        user_id  — str UUID of the actor
        action   — one of EventLog.Action constants
        changes  — dict from build_diff() or a manual before/after dict
        details  — dict of extra context (e.g. co-owner name, rejection reason)
    """
    payload = {'action': action}
    if changes:
        payload['changes'] = changes
    if details:
        payload['details'] = details

    EventLog.objects.create(
        id=str(uuid.uuid4()),
        event=event,
        edited_by_id=user_id,
        changed_fields=payload,
    )
