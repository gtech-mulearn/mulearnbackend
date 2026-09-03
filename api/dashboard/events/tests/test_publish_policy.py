"""Unit tests for the event publish routing policy.

These are deliberately DB-free: the policy is pure, so the whole decision
table can be exercised without a MySQL fixture.
"""
from datetime import timedelta
from types import SimpleNamespace

from django.utils import timezone

from db.events import Event
from utils.types import RoleType
from api.dashboard.events.publish_policy import (
    decide_publish_status,
    is_editable,
    resolve_terminal_status,
    should_announce,
)


def _event(*, starts_in, lasts=timedelta(hours=2)):
    """A stand-in carrying only the fields the policy reads."""
    start = timezone.now() + starts_in
    return SimpleNamespace(start_datetime=start, end_datetime=start + lasts)


# ─────────────────────────────────────────────────────────────
# resolve_terminal_status — the clock
# ─────────────────────────────────────────────────────────────

def test_event_that_already_ended_resolves_to_completed():
    event = _event(starts_in=timedelta(days=-30))
    assert resolve_terminal_status(event, Event.Status.PUBLISHED) == Event.Status.COMPLETED


def test_event_underway_right_now_resolves_to_ongoing():
    event = _event(starts_in=timedelta(hours=-1), lasts=timedelta(hours=3))
    assert resolve_terminal_status(event, Event.Status.PUBLISHED) == Event.Status.ONGOING


def test_future_event_stays_published():
    event = _event(starts_in=timedelta(days=7))
    assert resolve_terminal_status(event, Event.Status.PUBLISHED) == Event.Status.PUBLISHED


def test_pending_status_is_never_resolved_against_the_clock():
    """A past event awaiting review still has to be reviewed — the clock only
    applies once the pipeline has decided the event is publishable."""
    event = _event(starts_in=timedelta(days=-30))
    assert resolve_terminal_status(
        event, Event.Status.PENDING_CAMPUS_APPROVAL
    ) == Event.Status.PENDING_CAMPUS_APPROVAL


def test_event_with_no_dates_is_left_alone():
    event = SimpleNamespace(start_datetime=None, end_datetime=None)
    assert resolve_terminal_status(event, Event.Status.PUBLISHED) == Event.Status.PUBLISHED


# ─────────────────────────────────────────────────────────────
# decide_publish_status — the routing table
# ─────────────────────────────────────────────────────────────

def test_admin_publishes_directly():
    assert decide_publish_status(
        organiser_type=Event.OrganiserType.COMPANY,
        scope=Event.Scope.GLOBAL,
        roles=[RoleType.ADMIN.value],
        is_admin=True,
    ) == Event.Status.PUBLISHED


def test_campus_lead_publishes_own_campus_event_directly():
    assert decide_publish_status(
        organiser_type=Event.OrganiserType.CAMPUS,
        scope=Event.Scope.CAMPUS,
        roles=[RoleType.CAMPUS_LEAD.value],
        is_admin=False,
    ) == Event.Status.PUBLISHED


def test_campus_lead_publishes_globally_scoped_campus_event_without_admin():
    """Campus is the final authority for its own events at any scope."""
    assert decide_publish_status(
        organiser_type=Event.OrganiserType.CAMPUS,
        scope=Event.Scope.GLOBAL,
        roles=[RoleType.CAMPUS_LEAD.value],
        is_admin=False,
    ) == Event.Status.PUBLISHED


def test_campus_member_without_lead_role_goes_to_campus_review():
    assert decide_publish_status(
        organiser_type=Event.OrganiserType.CAMPUS,
        scope=Event.Scope.CAMPUS,
        roles=[RoleType.ENABLER.value],
        is_admin=False,
    ) == Event.Status.PENDING_CAMPUS_APPROVAL


def test_zonal_campus_lead_counts_as_campus_authority():
    assert decide_publish_status(
        organiser_type=Event.OrganiserType.CAMPUS,
        scope=Event.Scope.CAMPUS,
        roles=[RoleType.ZONAL_CAMPUS_LEAD.value],
        is_admin=False,
    ) == Event.Status.PUBLISHED


def test_campus_ig_event_by_campus_mentor_goes_to_campus_review():
    assert decide_publish_status(
        organiser_type=Event.OrganiserType.CAMPUS_IG,
        scope=Event.Scope.CAMPUS_IG,
        roles=[RoleType.MENTOR.value],
        is_admin=False,
        is_campus_mentor=True,
    ) == Event.Status.PENDING_CAMPUS_APPROVAL


def test_campus_ig_event_by_non_mentor_goes_to_mentor_review():
    assert decide_publish_status(
        organiser_type=Event.OrganiserType.CAMPUS_IG,
        scope=Event.Scope.CAMPUS_IG,
        roles=[RoleType.IG_LEAD.value],
        is_admin=False,
        is_campus_mentor=False,
    ) == Event.Status.PENDING_MENTOR_APPROVAL


def test_global_ig_event_by_assigned_ig_mentor_goes_to_admin_review():
    assert decide_publish_status(
        organiser_type=Event.OrganiserType.GLOBAL_IG,
        scope=Event.Scope.IG,
        roles=[RoleType.MENTOR.value],
        is_admin=False,
        is_ig_mentor_assigned=True,
    ) == Event.Status.PENDING_APPROVAL


def test_global_ig_event_by_unassigned_user_goes_to_mentor_review():
    assert decide_publish_status(
        organiser_type=Event.OrganiserType.GLOBAL_IG,
        scope=Event.Scope.IG,
        roles=[RoleType.IG_LEAD.value],
        is_admin=False,
        is_ig_mentor_assigned=False,
    ) == Event.Status.PENDING_MENTOR_APPROVAL


def test_company_event_by_owner_still_needs_admin_review():
    assert decide_publish_status(
        organiser_type=Event.OrganiserType.COMPANY,
        scope=Event.Scope.GLOBAL,
        roles=[RoleType.COMPANY.value],
        is_admin=False,
        is_company_owner=True,
    ) == Event.Status.PENDING_APPROVAL


def test_company_event_by_non_owner_goes_to_mentor_review():
    assert decide_publish_status(
        organiser_type=Event.OrganiserType.COMPANY,
        scope=Event.Scope.GLOBAL,
        roles=[RoleType.MENTOR.value],
        is_admin=False,
        is_company_owner=False,
    ) == Event.Status.PENDING_MENTOR_APPROVAL


def test_unrecognised_organiser_type_falls_back_to_admin_review():
    assert decide_publish_status(
        organiser_type="partner",
        scope=Event.Scope.GLOBAL,
        roles=[RoleType.IG_LEAD.value],
        is_admin=False,
    ) == Event.Status.PENDING_APPROVAL


# ─────────────────────────────────────────────────────────────
# should_announce — who gets told
# ─────────────────────────────────────────────────────────────

def test_newly_published_event_is_announced():
    assert should_announce(Event.Status.PUBLISHED) is True


def test_event_already_underway_is_announced():
    assert should_announce(Event.Status.ONGOING) is True


def test_event_that_already_finished_is_not_announced():
    """Broadcasting 'now live!' for something that ended last month is noise."""
    assert should_announce(Event.Status.COMPLETED) is False


def test_event_awaiting_review_is_not_announced():
    assert should_announce(Event.Status.PENDING_CAMPUS_APPROVAL) is False


# ─────────────────────────────────────────────────────────────
# is_editable — what an organiser can still change
# ─────────────────────────────────────────────────────────────

def test_completed_event_stays_editable():
    """A recorded past event is exactly the thing that needs correcting —
    a wrong date, a typo, a report link added afterwards."""
    assert is_editable(Event.Status.COMPLETED) is True


def test_cancelled_event_cannot_be_edited():
    assert is_editable(Event.Status.CANCELLED) is False


def test_draft_is_editable():
    assert is_editable(Event.Status.DRAFT) is True


def test_published_event_is_editable():
    assert is_editable(Event.Status.PUBLISHED) is True


# ─────────────────────────────────────────────────────────────
# The two composed — what the endpoint actually returns
# ─────────────────────────────────────────────────────────────

def test_campus_lead_publishing_a_past_event_gets_completed():
    """The reported bug: a campus recording an event it already ran."""
    event = _event(starts_in=timedelta(days=-14))
    routed = decide_publish_status(
        organiser_type=Event.OrganiserType.CAMPUS,
        scope=Event.Scope.CAMPUS,
        roles=[RoleType.CAMPUS_LEAD.value],
        is_admin=False,
    )
    assert resolve_terminal_status(event, routed) == Event.Status.COMPLETED


def test_campus_member_publishing_a_past_event_still_needs_campus_review():
    event = _event(starts_in=timedelta(days=-14))
    routed = decide_publish_status(
        organiser_type=Event.OrganiserType.CAMPUS,
        scope=Event.Scope.CAMPUS,
        roles=[RoleType.ENABLER.value],
        is_admin=False,
    )
    assert resolve_terminal_status(event, routed) == Event.Status.PENDING_CAMPUS_APPROVAL
