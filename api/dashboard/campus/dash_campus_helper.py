import uuid

from db.organization import UserOrganizationLink
from db.campus import CampusIGChapter
from db.user import Role, UserRoleLink
from utils.types import OrganizationType, RoleType


def get_user_college_link(user_id):
    return UserOrganizationLink.objects.filter(
        user_id=user_id,
        org__org_type=OrganizationType.COLLEGE.value
    ).first()


def get_campus_context(request):
    """
    Standardized tenancy enforcement helper.
    Returns (org, error_response).
    """
    from utils.permission import JWTUtils
    from utils.response import CustomResponse
    from rest_framework import status

    user_id = JWTUtils.fetch_user_id(request)
    link = get_user_college_link(user_id)
    
    if not link or not link.org:
        return None, CustomResponse(
            general_message="User is not linked to a campus",
            message={"error_code": "CAMPUS_NOT_FOUND"},
        ).get_failure_response(
            status_code=404,
            http_status_code=status.HTTP_404_NOT_FOUND,
        )
    
    return link.org, None


def validate_campus_member(user_id, org_id):
    """Confirm that a user is an active member of the given campus (not alumni)."""
    return UserOrganizationLink.objects.filter(
        user_id=user_id,
        org_id=org_id,
        org__org_type=OrganizationType.COLLEGE.value,
        is_alumni=False,
    ).exists()


def get_campus_ig_chapters(org_id):
    """Return active IG chapters for a campus, with related IG and lead pre-fetched."""
    return CampusIGChapter.objects.filter(
        org_id=org_id,
        is_active=True,
    ).select_related("ig", "lead")


def assign_ig_campus_lead(chapter, new_lead, acting_user_id):
    """
    Assign a new campus-level IG lead for a chapter.
    - Removes the old lead's UserRoleLink for "{ig_code} CampusLead" at this campus.
    - Creates a new UserRoleLink for the new lead.
    - Updates the chapter's lead field.
    Mirrors the role-transfer logic in TransferIGRoleAPI.post().
    """
    ig_code = chapter.ig.code
    role = Role.objects.filter(title=RoleType.IG_CAMPUS_LEAD_ROLE(ig_code)).first()
    if role is None:
        return False

    # Remove existing campus-level IG lead role for this campus
    UserRoleLink.objects.filter(
        user__user_organization_link_user__org=chapter.org,
        user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
        role=role,
    ).delete()

    # Assign role to new lead
    UserRoleLink.objects.create(
        id=str(uuid.uuid4()),
        user=new_lead,
        role=role,
        verified=True,
        created_by_id=acting_user_id,
    )

    # Update chapter lead
    chapter.lead = new_lead
    chapter.updated_by_id = acting_user_id
    chapter.save()

    return True


def get_campus_events_qs(org):
    from api.dashboard.events.serializers import get_live_events
    from db.events import Event

    base = get_live_events()
    return (
        base.filter(scope=Event.Scope.CAMPUS, scope_org=org)
        | base.filter(scope=Event.Scope.CAMPUS_IG, scope_org=org)
    ).distinct()