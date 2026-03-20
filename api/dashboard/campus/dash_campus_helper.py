import uuid

from db.organization import UserOrganizationLink
from db.campus import CampusIGChapter
from db.user import Role, UserRoleLink
from utils.types import OrganizationType


def get_user_college_link(user_id):
    return UserOrganizationLink.objects.filter(
        user_id=user_id,
        org__org_type=OrganizationType.COLLEGE.value
    ).first()


def validate_campus_member(user_id, org_id):
    """Confirm that a user is a member of the given campus."""
    return UserOrganizationLink.objects.filter(
        user_id=user_id,
        org_id=org_id,
        org__org_type=OrganizationType.COLLEGE.value,
    ).first()


def get_campus_ig_chapters(org_id):
    """Return active IG chapters for a campus, with related IG and lead pre-fetched."""
    return CampusIGChapter.objects.filter(
        org_id=org_id,
        is_active=True,
    ).select_related('ig', 'lead')


def assign_ig_campus_lead(chapter, new_lead, acting_user_id):
    """
    Assign a new campus-level IG lead for a chapter.

    - Removes the old lead's UserRoleLink for {ig_code}CampusLead at this campus.
    - Creates a new UserRoleLink for the new lead.
    - Updates the chapter's lead field.

    Mirrors the role-transfer logic in TransferIGRoleAPI.post().
    """
    ig_code = chapter.ig.code
    role = Role.objects.filter(title=f"{ig_code}CampusLead").first()
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
