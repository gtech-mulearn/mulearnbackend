from db.organization import UserOrganizationLink, Organization
from utils.types import OrganizationType


def get_user_college_link(user_id):
    return UserOrganizationLink.objects.filter(
        user_id=user_id, org__org_type=OrganizationType.COLLEGE.value
    ).first()


def get_user_college(user_id):
    return Organization.objects.filter(
        user_organization_link_org_id__user_id=user_id,
        org_type=OrganizationType.COLLEGE.value
    ).first()
