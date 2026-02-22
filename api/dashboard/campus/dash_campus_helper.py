import uuid

from db.campus import CampusIGChapter
from db.organization import UserOrganizationLink
from db.user import Role, UserRoleLink
from utils.types import OrganizationType
from utils.utils import DateTimeUtils


def get_user_college_link(user_id):
    return UserOrganizationLink.objects.filter(
        user_id=user_id,
        org__org_type=OrganizationType.COLLEGE.value
    ).first()


def validate_campus_member(user_id, org):
    """Returns True if the given user_id has a UserOrganizationLink
    for this org with org_type=COLLEGE. False otherwise."""
    return UserOrganizationLink.objects.filter(
        user_id=user_id,
        org=org,
        org__org_type=OrganizationType.COLLEGE.value,
    ).exists()


def get_campus_ig_chapter(chapter_id, org):
    """Returns CampusIGChapter if it belongs to org, else None.
    Always scope by org to prevent cross-campus access."""
    return CampusIGChapter.objects.filter(id=chapter_id, org=org).first()


def assign_ig_lead_role(user, ig, org, created_by_id):
    """Upserts a UserRoleLink for the IG Lead role (title = ig.code + 'CampusLead').
    Removes any existing holder of that role in this campus first.
    Mirrors the logic in TransferIGRoleAPI."""
    role = Role.objects.filter(title=f'{ig.code}CampusLead').first()
    if role is None:
        return None, 'IG lead role not found'
    # Remove old lead in this campus
    UserRoleLink.objects.filter(
        user__user_organization_link_user__org=org,
        role=role,
    ).delete()
    # Assign new lead
    UserRoleLink.objects.create(
        id=str(uuid.uuid4()),
        user=user,
        role=role,
        verified=True,
        created_by_id=created_by_id,
        created_at=DateTimeUtils.get_current_utc_time(),
    )
    return role, None
