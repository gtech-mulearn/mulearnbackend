import uuid

from db.organization import UserOrganizationLink
from db.campus import CampusIGChapter, CampusExecomRole
from db.user import Role, UserRoleLink
from utils.types import OrganizationType, RoleType


def get_user_college_link(user_id):
    """
    Return the user's college org link, preferring a verified membership.
    A newer unverified link (e.g. a pending college-transfer request) should
    not silently override an established verified membership.
    """
    links = UserOrganizationLink.objects.filter(
        user_id=user_id,
        org__org_type=OrganizationType.COLLEGE.value
    ).order_by("-created_at", "-id")
    return links.filter(verified=True).first() or links.first()


def is_approved_campus_mentor(user_id, org):
    """
    Return True if the user holds an active CAMPUS_MENTOR grant scoped to the given org.
    """
    if org is None:
        return False
    from db.user import MentorScopeGrant
    from api.dashboard.mentor.dash_mentor_helper import has_scope
    return has_scope(user_id, MentorScopeGrant.ScopeType.CAMPUS_MENTOR, org.id)


def campus_staff_required(view_func):
    """
    Decorator that allows access to Campus Leads, Lead Enablers, Enablers,
    AND approved Campus Mentors (read-only campus dashboard endpoints).

    Enablers get read-only access to their own campus: this decorator only
    guards GET handlers; all mutating endpoints are gated separately by
    @role_required([CAMPUS_LEAD, LEAD_ENABLER]).

    Usage:
        @campus_staff_required
        def get(self, request): ...
    """
    from utils.permission import JWTUtils
    from utils.response import CustomResponse

    _STAFF_ROLES = {
        RoleType.CAMPUS_LEAD.value,
        RoleType.LEAD_ENABLER.value,
        RoleType.ENABLER.value,
    }

    def wrapped(obj, request, *args, **kwargs):
        user_id = JWTUtils.fetch_user_id(request)
        roles = set(JWTUtils.fetch_role(request))

        # Fast path: JWT role is Campus Lead or Lead Enabler
        if roles & _STAFF_ROLES:
            return view_func(obj, request, *args, **kwargs)

        # Slow path: check if the user is an approved Campus Mentor
        # for *their* campus (fetched from org link)
        user_link = get_user_college_link(user_id)
        if user_link and is_approved_campus_mentor(user_id, user_link.org):
            return view_func(obj, request, *args, **kwargs)

        return CustomResponse(
            general_message="You do not have the required role to access this page."
        ).get_failure_response()

    return wrapped


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


def normalize_role_title(raw_title):
    """
    Collapse whitespace and Title Case a brand-new execom role title.
    Only call this when actually creating a new CampusExecomRole row — an
    existing row's stored casing should always win over re-normalizing it
    (str.title() mis-cases things like "IG Lead" -> "Ig Lead" on repeat submits).
    """
    return " ".join(raw_title.strip().split()).title()


def ig_synthetic_titles_for_org(org):
    """
    The dynamically-computed set of IG-derived execom-assignable titles valid for this campus —
    a CampusIGLead + CampusIGCoLead pair per active CampusIGChapter. This is the single source of
    truth both CampusExecomRoleAPI.get (merge) and CampusExecomAPI.post (validation) use, so the
    two never drift apart.

    Deliberately excludes "{code} IGLead" — that title is a plain, non-execom IG membership role
    (is_execom_role=False, see assign_ig_campus_lead) and must never appear in an execom roles
    fetcher response.
    """
    titles = set()
    for chapter in CampusIGChapter.objects.filter(org=org, is_active=True).select_related("ig"):
        if chapter.ig:
            titles.add(RoleType.IG_CAMPUS_LEAD_ROLE(chapter.ig.code))
            titles.add(RoleType.IG_CAMPUS_COLEAD_ROLE(chapter.ig.code))
    return titles


def match_ig_code_from_title(title):
    """
    If `title` exactly matches one of the IG-synthetic patterns for a REAL InterestGroup code
    ("{code} CampusIGLead" / "{code} IGLead" / "{code} CampusIGCoLead"), return that code
    (case-insensitive); else None. Used to keep campus_execom_role's global catalog free of
    IG-scoped titles, which must stay campus-filtered rather than shown to every campus.
    """
    from db.task import InterestGroup

    for suffix in ("CampusIGLead", "IGLead", "CampusIGCoLead"):
        if title.lower().endswith(f" {suffix.lower()}"):
            code = title[: -(len(suffix) + 1)].strip()
            if InterestGroup.objects.filter(code__iexact=code).exists():
                return code
    return None


def ensure_ig_execom_catalog_entries(ig_code, ig_name, acting_user_id):
    """
    Ensure this IG's execom-assignable titles (CampusIGLead, CampusIGCoLead — never the plain,
    non-execom "{code} IGLead") exist in the global campus_execom_role directory (case-insensitive,
    no duplicates). Called whenever an IG chapter is created or its lead is (re)assigned, so the
    roles are immediately visible/reusable once relevant.
    """
    for title in (
        RoleType.IG_CAMPUS_LEAD_ROLE(ig_code),
        RoleType.IG_CAMPUS_COLEAD_ROLE(ig_code),
    ):
        # Atomic get-or-create: title has a case-insensitive unique constraint, so a
        # separate check-then-create is racy under concurrent chapter creation — two
        # requests can both pass the check and then one hits an IntegrityError on
        # insert. get_or_create retries the lookup on that IntegrityError instead.
        CampusExecomRole.objects.get_or_create(
            title=title,
            defaults={
                "id": str(uuid.uuid4()),
                "description": f"{ig_name} Interest Group role",
                "created_by_id": acting_user_id,
                "updated_by_id": acting_user_id,
            },
        )


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
    - Removes the old lead's UserRoleLink for "{ig_code} CampusIGLead" at this campus.
    - Creates a new UserRoleLink for the new lead.
    - Updates the chapter's lead field.
    Mirrors the role-transfer logic in TransferIGRoleAPI.post().
    """
    ig_code = chapter.ig.code
    ig_name = chapter.ig.name

    roles_to_ensure = [
        {
            "title": ig_name,
            "description": f"{ig_name} Interest Group Member",
            "is_execom_role": False,
        },
        {
            "title": RoleType.IG_CAMPUS_LEAD_ROLE(ig_code),
            "description": f"{ig_name} Interest Group Campus Lead",
            "is_execom_role": True,
        },
        {
            "title": RoleType.IG_CAMPUS_COLEAD_ROLE(ig_code),
            "description": f"{ig_name} Interest Group Campus Co-Lead",
            "is_execom_role": True,
        },
        {
            "title": RoleType.IG_LEAD_ROLE(ig_code),
            "description": f"{ig_name} Interest Group Lead",
            "is_execom_role": False,
        },
    ]

    for role_data in roles_to_ensure:
        Role.objects.get_or_create(
            title=role_data["title"],
            defaults={
                "id": str(uuid.uuid4()),
                "description": role_data["description"],
                "created_by_id": acting_user_id,
                "updated_by_id": acting_user_id,
                "is_execom_role": role_data["is_execom_role"],
            }
        )

    # Keep the global role directory in sync with this IG's assignable titles.
    ensure_ig_execom_catalog_entries(ig_code, ig_name, acting_user_id)

    role = Role.objects.get(title=RoleType.IG_CAMPUS_LEAD_ROLE(ig_code))

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