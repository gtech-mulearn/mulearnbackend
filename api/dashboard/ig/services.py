from django.db.models import Count, Q
from db.task import InterestGroup, UserIgLink
from utils.types import OrganizationType

def get_campus_igs(org_id: str):
    """
    Returns active Interest Groups within a campus based on actual student membership.
    Enforces tenant isolation by strictly filtering user_ig_link by the given org_id.
    """
    return InterestGroup.objects.filter(
        user_ig_link_ig__user__user_organization_link_user__org_id=org_id,
        user_ig_link_ig__user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value
    ).annotate(
        campus_member_count=Count(
            'user_ig_link_ig__user', 
            distinct=True,
            filter=Q(
                user_ig_link_ig__user__user_organization_link_user__org_id=org_id,
                user_ig_link_ig__user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value
            )
        )
    ).distinct()

def get_top_igs(org_id: str):
    return get_campus_igs(org_id).order_by('-campus_member_count')

def get_ig_members(ig_id: str, org_id: str):
    return UserIgLink.objects.filter(
        ig_id=ig_id,
        user__user_organization_link_user__org_id=org_id,
        user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value
    ).select_related('user', 'user__wallet_user', 'user__user_lvl_link_user__level')
