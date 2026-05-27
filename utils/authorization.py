from dataclasses import dataclass, field
from typing import Set, Optional, List
from django.db.models import Prefetch

from db.user import User
from utils.types import RoleType, OrganizationType

@dataclass
class AuthContext:
    user_id: str
    roles: List[str]
    org_id: Optional[str]
    org_path: Optional[str]
    is_global: bool
    capabilities: Set[str] = field(default_factory=set)

    @property
    def is_authorized(self):
        return True


# Define static capabilities explicitly by Tier/Role
CAPABILITIES = {
    # Campus Mentor Capabilities
    'CAMPUS_MENTOR': {
        'campus:event:manage',
        'campus:event:view',
        'campus:execom:manage',
        'campus:execom:view',
        'campus:students:view',
        'campus:dashboard:view',
        'campus:lc:manage',
        'campus:ig:manage',
        'campus:analytics:view',
    },
    
    # Company Mentor Capabilities
    'COMPANY_MENTOR': {
        'company:job:manage',
        'company:event:manage',
        'company:students:view',
        'company:dashboard:view',
        'company:analytics:view',
    },

    # Campus Lead Capabilities (Legacy backward compatibility mapping)
    RoleType.CAMPUS_LEAD.value: {
        'campus:event:manage',
        'campus:event:view',
        'campus:execom:manage',
        'campus:execom:view',
        'campus:students:view',
        'campus:dashboard:view',
        'campus:lc:manage',
        'campus:ig:manage',
        'campus:analytics:view',
    },

    # Company Capabilities (Legacy backward compatibility mapping)
    RoleType.COMPANY.value: {
        'company:job:manage',
        'company:event:manage',
        'company:students:view',
        'company:dashboard:view',
        'company:analytics:view',
    },

    # Lead Enabler Capabilities
    RoleType.LEAD_ENABLER.value: {
        'campus:event:manage',
        'campus:event:view',
        'campus:execom:manage',
        'campus:execom:view',
        'campus:students:view',
        'campus:dashboard:view',
        'campus:lc:manage',
        'campus:ig:manage',
        'campus:analytics:view',
    }
}


def resolve_capabilities(roles: List[str], mentor_tiers: List[str]) -> Set[str]:
    """
    Resolves the combined set of capabilities for a given list of roles and mentor tiers.
    """
    capabilities = set()
    for tier in mentor_tiers:
        if tier in CAPABILITIES:
            capabilities.update(CAPABILITIES[tier])
    for role in roles:
        if role in CAPABILITIES:
            capabilities.update(CAPABILITIES[role])
    return capabilities


def build_auth_context(user: User) -> AuthContext:
    """
    Builds the AuthContext by resolving user's mentor and organization links.
    Assumes `user_mentor_user` and `user_organization_link_user` and `user_role_link_user` are prefetched.
    """
    is_global = False
    org_id = None
    mentor_tiers = []
    roles = []
    
    if getattr(user, 'admin', False):
        is_global = True
    
    # Check mentor links first
    # Using the related name `user_mentor_user` from db.user.UserMentor
    for mentor_link in user.user_mentor_user.all():
        mentor_tiers.append(mentor_link.mentor_tier)
        if mentor_link.mentor_tier == 'MENTOR':
            is_global = True
        elif mentor_link.mentor_tier in ['CAMPUS_MENTOR', 'COMPANY_MENTOR']:
            if mentor_link.org_id:
                org_id = mentor_link.org_id

    # Gather regular roles from UserRoleLink
    # Related name: user_role_link_user
    for role_link in user.user_role_link_user.all():
        if role_link.role and role_link.role.title:
            roles.append(role_link.role.title)
            # Global Admins bypass org checks
            if role_link.role.title == RoleType.ADMIN.value:
                is_global = True

    # If the user isn't a scoped mentor or global admin, fallback to UserOrganizationLink 
    # to support legacy Leads/Students (e.g. Campus Leads)
    if not is_global and not org_id:
        # Check for campus lead role / enabler
        # This resolves the implicit org_id for Campus Dashboard
        if any(role in roles for role in [RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value]):
            for org_link in user.user_organization_link_user.all():
                if org_link.org and org_link.org.org_type == OrganizationType.COLLEGE.value:
                    org_id = org_link.org_id
                    break
        elif RoleType.COMPANY.value in roles:
            from db.company import Company
            company = Company.objects.filter(company_user_id=user).first()
            if company:
                org_id = company.id
                    
    capabilities = resolve_capabilities(roles, mentor_tiers)
    
    return AuthContext(
        user_id=user.id,
        roles=roles,
        org_id=org_id,
        org_path=None, # Deferred materialized paths
        is_global=is_global,
        capabilities=capabilities
    )
