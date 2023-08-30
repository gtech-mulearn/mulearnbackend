from db.organization import UserOrganizationLink, Organization
from utils.types import OrganizationType


def get_user_college_link(user_id):
    return UserOrganizationLink.objects.filter(
        user_id=user_id, org__org_type=OrganizationType.COLLEGE.value
    ).first()
