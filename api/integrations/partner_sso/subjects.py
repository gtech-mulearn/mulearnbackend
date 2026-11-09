"""
Who may act for which partner account (spec B §3.1).

Every check reads the DB: JWTs include unverified role links
(docs/superpowers/specs/2026-09-25-role-verification-security-findings.md).
Adapters map their own account types onto these µLearn subject kinds.
"""
from dataclasses import dataclass
from enum import Enum

from db.company import Company, CompanyAdminLink
from db.organization import UserOrganizationLink
from db.user import User, UserRoleLink
from utils.types import OrganizationType, RoleType


class SubjectKind(str, Enum):
    LEARNER = "learner"
    COMPANY = "company"
    COLLEGE = "college"


LEARNER_ROLES = (RoleType.STUDENT.value, RoleType.MULEARNER.value)
CAMPUS_STAFF_ROLES = (RoleType.CAMPUS_LEAD.value, RoleType.ENABLER.value, RoleType.LEAD_ENABLER.value)
CAMPUS_ORG_TYPES = (OrganizationType.COLLEGE.value, OrganizationType.SCHOOL.value)

# The card does not render at all for these (spec B §3.1).
HIDDEN_REASONS = frozenset({"not_learner", "suspended", "not_company_member", "not_campus_staff"})

REASON_MESSAGES = {
    "company_not_verified": "Available once µLearn verifies your company.",
    "not_owner": "Managed by your company's owner.",
    "not_lead_enabler": "Managed by your college's Lead Enabler.",
    "no_lead_enabler": "Your college has no Lead Enabler yet.",
    "multiple_lead_enablers": "Your college has more than one Lead Enabler. Contact µLearn support.",
}


@dataclass(frozen=True)
class Resolution:
    kind: SubjectKind
    reason: str | None = None
    subject_type: str | None = None
    subject_id: str | None = None
    subject_name: str | None = None
    manager: object = None  # the User who manages the subject and is its contact
    can_manage: bool = False

    @property
    def hidden(self):
        return self.reason in HIDDEN_REASONS

    @property
    def message(self):
        return REASON_MESSAGES.get(self.reason)


def resolve(kind, user_id):
    return _RESOLVERS[SubjectKind(kind)](user_id)


def _learner(user_id):
    user = _active_user(user_id)
    if user is None:
        return Resolution(SubjectKind.LEARNER, reason="suspended")
    if not _has_active_role(user_id, LEARNER_ROLES):
        return Resolution(SubjectKind.LEARNER, reason="not_learner")
    return Resolution(SubjectKind.LEARNER, subject_type="user", subject_id=user.id,
                      subject_name=user.full_name, manager=user, can_manage=True)


def _company(user_id):
    owned = _owned_company(user_id)
    if owned is not None:
        base = {"kind": SubjectKind.COMPANY, "subject_type": "company",
                "subject_id": owned.id, "subject_name": owned.name}
        if owned.status != "verified":
            return Resolution(**base, reason="company_not_verified")
        owner = _active_user(user_id)
        if owner is None:
            return Resolution(SubjectKind.COMPANY, reason="suspended")
        return Resolution(**base, manager=owner, can_manage=True)
    delegated = _delegated_company(user_id)
    if delegated is not None:
        return Resolution(SubjectKind.COMPANY, reason="not_owner", subject_type="company",
                          subject_id=delegated.id, subject_name=delegated.name, manager=delegated.company_user)
    return Resolution(SubjectKind.COMPANY, reason="not_company_member")


def _college(user_id):
    link = _campus_link(user_id)
    if link is None or not _has_active_role(user_id, CAMPUS_STAFF_ROLES):
        return Resolution(SubjectKind.COLLEGE, reason="not_campus_staff")
    org = link.org
    base = {"kind": SubjectKind.COLLEGE, "subject_type": "organization",
            "subject_id": org.id, "subject_name": org.title}
    leads = _lead_enablers(org.id)
    if len(leads) > 1:
        # Two contacts would keep replacing each other at Futuremug.
        return Resolution(**base, reason="multiple_lead_enablers")
    if not leads:
        return Resolution(**base, reason="no_lead_enabler")
    lead = leads[0]
    if lead.id != user_id:
        return Resolution(**base, reason="not_lead_enabler", manager=lead)
    return Resolution(**base, manager=lead, can_manage=True)


_RESOLVERS = {SubjectKind.LEARNER: _learner, SubjectKind.COMPANY: _company, SubjectKind.COLLEGE: _college}


# ── Queries: small, so tests can patch them ───────────────────────────────

def _active_user(user_id):
    return User.objects.filter(id=user_id).first()  # ActiveUserManager hides suspended users


def _has_active_role(user_id, titles):
    return UserRoleLink.objects.filter(
        user_id=user_id, role__title__in=titles, ig__isnull=True,
        verified=True, is_active=True, revoked_at__isnull=True,
    ).exists()


def _owned_company(user_id):
    return Company.objects.filter(company_user_id=user_id).first()


def _delegated_company(user_id):
    link = (CompanyAdminLink.objects
            .filter(user_id=user_id, status=CompanyAdminLink.Status.ACCEPTED)
            .select_related("company__company_user").first())
    return link.company if link else None


def _campus_link(user_id):
    return (UserOrganizationLink.objects
            .filter(user_id=user_id, org__org_type__in=CAMPUS_ORG_TYPES, verified=True)
            .select_related("org").order_by("-created_at", "-id").first())


def _lead_enablers(org_id):
    """At most two: enough to tell none, one and too many apart."""
    return list(User.objects.filter(
        user_role_link_user__role__title=RoleType.LEAD_ENABLER.value,
        user_role_link_user__ig__isnull=True,
        user_role_link_user__verified=True,
        user_role_link_user__is_active=True,
        user_role_link_user__revoked_at__isnull=True,
        user_organization_link_user__org_id=org_id,
        user_organization_link_user__verified=True,
    ).distinct()[:2])
