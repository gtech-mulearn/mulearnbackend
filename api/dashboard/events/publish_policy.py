"""Publish routing policy for events.

Kept free of DB access on purpose: the caller resolves the mentor grants and
company ownership it needs, then this module makes the decision. That keeps
the whole routing table testable without a MySQL fixture, and keeps the one
rule about *when* an event is publishable in a single place rather than
duplicated across the publish and approve endpoints.
"""
from django.utils import timezone

from db.events import Event
from utils.types import RoleType


# Roles that speak for a campus. A campus is the final authority on its own
# events, so any of these publishes a campus event outright.
CAMPUS_AUTHORITY_ROLES = frozenset({
    RoleType.CAMPUS_LEAD.value,
    RoleType.ZONAL_CAMPUS_LEAD.value,
    RoleType.DISTRICT_CAMPUS_LEAD.value,
})


def decide_publish_status(
    *,
    organiser_type,
    scope,
    roles,
    is_admin,
    is_campus_mentor=False,
    is_ig_mentor_assigned=False,
    is_company_owner=False,
):
    """Which status a publish request moves an event into, before the clock.

    `scope` is part of the context but is deliberately *not* consulted for
    campus events: a campus owns its events at every scope, so widening the
    audience no longer diverts them to admin review.
    """
    if is_admin:
        return Event.Status.PUBLISHED

    if organiser_type == Event.OrganiserType.CAMPUS_IG:
        return (Event.Status.PENDING_CAMPUS_APPROVAL if is_campus_mentor
                else Event.Status.PENDING_MENTOR_APPROVAL)

    if organiser_type == Event.OrganiserType.GLOBAL_IG:
        return (Event.Status.PENDING_APPROVAL if is_ig_mentor_assigned
                else Event.Status.PENDING_MENTOR_APPROVAL)

    if organiser_type == Event.OrganiserType.CAMPUS:
        return (Event.Status.PUBLISHED if CAMPUS_AUTHORITY_ROLES.intersection(roles)
                else Event.Status.PENDING_CAMPUS_APPROVAL)

    if organiser_type == Event.OrganiserType.COMPANY:
        # Company events always need admin sign-off (PRD §3.1); the owner's
        # own leg is the only one they get to skip.
        return (Event.Status.PENDING_APPROVAL if is_company_owner
                else Event.Status.PENDING_MENTOR_APPROVAL)

    return Event.Status.PENDING_APPROVAL


def resolve_terminal_status(event, routed_status, now=None):
    """Settle a publishable event against the clock.

    An event the pipeline has cleared lands in its real lifecycle state, so a
    campus can record something it already ran instead of being told the start
    date must be in the future. Anything still awaiting review passes through
    untouched — a past date does not excuse an event from its approval step.
    """
    if routed_status != Event.Status.PUBLISHED:
        return routed_status

    now = now or timezone.now()
    if event.end_datetime and event.end_datetime <= now:
        return Event.Status.COMPLETED
    if event.start_datetime and event.start_datetime <= now:
        return Event.Status.ONGOING
    return Event.Status.PUBLISHED


def is_editable(status):
    """Whether an organiser can still change an event in `status`.

    Completed events stay editable on purpose: an event recorded after the
    fact lands there immediately, and correcting it — a wrong date, a typo,
    a write-up added later — is the whole point of being able to record one.
    Cancelled events are a tombstone and stay frozen.
    """
    return status != Event.Status.CANCELLED


def should_announce(status):
    """Whether reaching `status` is worth broadcasting to an audience.

    An event recorded after the fact lands straight in COMPLETED; telling
    people it is "now live" would be noise, so only events someone can still
    turn up to get announced.
    """
    return status in (Event.Status.PUBLISHED, Event.Status.ONGOING)
