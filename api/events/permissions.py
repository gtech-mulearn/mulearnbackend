"""
Event-specific permission helpers.

These functions check ownership, co-ownership, and organisational role
authority for event management operations.
"""

from db.event import Event, EventCoOwner, EventOrganiser
from db.organization import Organization, UserOrganizationLink
from db.task import InterestGroup, UserIgLink
from db.user import UserRoleLink
from utils.types import RoleType


def is_event_owner_or_coowner(user_id: str, event: Event) -> bool:
    """Return True if user is the event creator or a co-owner."""
    if event.created_by_id == user_id:
        return True
    return EventCoOwner.objects.filter(event=event, user_id=user_id).exists()


def get_user_roles(user_id: str) -> list[str]:
    """Return list of role titles for a user."""
    return list(
        UserRoleLink.objects.filter(user_id=user_id, verified=True)
        .values_list("role__title", flat=True)
    )


def has_role(user_id: str, role_title: str) -> bool:
    """Check if user has a specific verified role."""
    return UserRoleLink.objects.filter(
        user_id=user_id,
        role__title=role_title,
        verified=True,
    ).exists()


def is_admin(user_id: str) -> bool:
    return has_role(user_id, RoleType.ADMIN.value)


def is_mentor(user_id: str) -> bool:
    return has_role(user_id, RoleType.MENTOR.value)


def is_campus_lead_of(user_id: str, org_id: str) -> bool:
    """Check if user is the Campus Lead of a given organization (campus)."""
    return has_role(user_id, RoleType.CAMPUS_LEAD.value) and \
        UserOrganizationLink.objects.filter(user_id=user_id, org_id=org_id).exists()


def is_ig_lead_of(user_id: str, ig_id: str) -> bool:
    """Check if user is the IG Lead of a given Interest Group."""
    ig = InterestGroup.objects.filter(id=ig_id).first()
    if not ig:
        return False
    ig_lead_role = RoleType.IG_LEAD_ROLE(ig.code)
    return has_role(user_id, ig_lead_role)


def is_campus_ig_lead_of(user_id: str, org_id: str, ig_id: str) -> bool:
    """Check if user is the Campus IG Lead for a specific campus-IG chapter."""
    ig = InterestGroup.objects.filter(id=ig_id).first()
    if not ig:
        return False
    cig_lead_role = RoleType.IG_CAMPUS_LEAD_ROLE(ig.code)
    return has_role(user_id, cig_lead_role) and \
        UserOrganizationLink.objects.filter(user_id=user_id, org_id=org_id).exists()


def can_approve_event(user_id: str, event: Event) -> tuple[bool, str]:
    """
    Check if a user can approve an event based on its current status.
    Returns (can_approve, new_status) or (False, '').
    """
    if is_admin(user_id):
        # Admin can approve any pending event to published
        if event.status in (
            Event.Status.PENDING_CAMPUS_APPROVAL,
            Event.Status.PENDING_APPROVAL,
            Event.Status.PENDING_MENTOR_APPROVAL,
        ):
            return True, Event.Status.PUBLISHED
        return False, ''

    organiser = EventOrganiser.objects.filter(event=event).first()
    if not organiser:
        return False, ''

    if event.status == Event.Status.PENDING_CAMPUS_APPROVAL:
        # Campus Lead of the chapter's campus approves step 1
        ci_org_id = organiser.ci_org_id_id if organiser.organiser_type == 'campus_ig' else None
        if ci_org_id and is_campus_lead_of(user_id, ci_org_id):
            return True, Event.Status.PENDING_APPROVAL

    elif event.status == Event.Status.PENDING_APPROVAL:
        # GIG Lead of that IG approves step 2 (campus_ig events)
        # or Admin approves (handled above)
        ig_id = None
        if organiser.organiser_type == 'campus_ig':
            ig_id = organiser.ci_ig_id_id
        elif organiser.organiser_type == 'global_ig':
            ig_id = organiser.ig_id_id
        if ig_id and is_ig_lead_of(user_id, ig_id):
            return True, Event.Status.PUBLISHED

    elif event.status == Event.Status.PENDING_MENTOR_APPROVAL:
        # Mentor approves GIG Lead events
        if is_mentor(user_id):
            return True, Event.Status.PUBLISHED

    return False, ''


def can_reject_event(user_id: str, event: Event) -> bool:
    """Check if a user can reject an event — same actors who can approve."""
    can, _ = can_approve_event(user_id, event)
    return can


def determine_initial_status(organiser_type: str, user_id: str, org_id: str = None) -> str:
    """
    Determine what status an event should start at based on organiser type
    and the creator's role.
    """
    if organiser_type == EventOrganiser.OrganiserType.ADMIN:
        return Event.Status.DRAFT

    if organiser_type == EventOrganiser.OrganiserType.CAMPUS:
        return Event.Status.DRAFT

    if organiser_type == EventOrganiser.OrganiserType.COMPANY:
        return Event.Status.DRAFT

    if organiser_type == EventOrganiser.OrganiserType.CAMPUS_IG:
        # If the Campus Lead creates a campus_ig event, skip campus approval
        if org_id and is_campus_lead_of(user_id, org_id):
            return Event.Status.PENDING_APPROVAL
        return Event.Status.PENDING_CAMPUS_APPROVAL

    if organiser_type == EventOrganiser.OrganiserType.GLOBAL_IG:
        return Event.Status.PENDING_MENTOR_APPROVAL

    return Event.Status.DRAFT
