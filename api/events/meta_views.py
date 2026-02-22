"""
Meta endpoints — form selector population.

GET events/meta/organizer-options/      — entities the user can create events as
GET events/meta/collaboration-targets/  — searchable entities for collaborator invites
"""

from rest_framework.views import APIView

from db.organization import Organization, UserOrganizationLink
from db.task import InterestGroup, UserIgLink
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from .permissions import get_user_roles, has_role


class OrganizerOptionsAPI(APIView):
    """
    GET events/meta/organizer-options/

    Returns the entities the authenticated user can create events as,
    based on their roles and org/IG memberships.
    """

    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        roles = get_user_roles(user_id)
        options = []

        # Admin can create events as admin
        if RoleType.ADMIN.value in roles:
            options.append({
                "organiser_type": "admin",
                "label": "μLearn (Admin)",
                "entity_id": None,
            })

        # Campus Lead — can create campus events for their campuses
        if RoleType.CAMPUS_LEAD.value in roles:
            campuses = (
                UserOrganizationLink.objects
                .filter(user_id=user_id)
                .select_related("org")
                .filter(org__org_type=OrganizationType.COLLEGE.value)
            )
            for link in campuses:
                options.append({
                    "organiser_type": "campus",
                    "label": link.org.title,
                    "entity_id": link.org_id,
                })

                # Campus Lead can also create campus_ig events for IGs in their campus
                # List available IGs for each campus
                ig_links = UserIgLink.objects.filter(user_id=user_id).select_related("ig")
                for ig_link in ig_links:
                    options.append({
                        "organiser_type": "campus_ig",
                        "label": f"{link.org.title} × {ig_link.ig.name}",
                        "entity_id": {
                            "org_id": link.org_id,
                            "ig_id": ig_link.ig_id,
                        },
                    })

        # IG Lead — can create global IG events for their IGs
        ig_links = UserIgLink.objects.filter(user_id=user_id).select_related("ig")
        for ig_link in ig_links:
            ig = ig_link.ig
            ig_lead_role = RoleType.IG_LEAD_ROLE(ig.code)
            if ig_lead_role in roles:
                options.append({
                    "organiser_type": "global_ig",
                    "label": f"{ig.name} (IG Lead)",
                    "entity_id": ig.id,
                })

        # Campus IG Lead — can create campus_ig events
        for ig_link in ig_links:
            ig = ig_link.ig
            cig_lead_role = RoleType.IG_CAMPUS_LEAD_ROLE(ig.code)
            if cig_lead_role in roles:
                # Find the campuses this user is linked to
                campus_links = (
                    UserOrganizationLink.objects
                    .filter(user_id=user_id)
                    .select_related("org")
                    .filter(org__org_type=OrganizationType.COLLEGE.value)
                )
                for campus_link in campus_links:
                    options.append({
                        "organiser_type": "campus_ig",
                        "label": f"{campus_link.org.title} × {ig.name}",
                        "entity_id": {
                            "org_id": campus_link.org_id,
                            "ig_id": ig.id,
                        },
                    })

        # Company — can create company events
        if RoleType.COMPANY.value in roles:
            companies = (
                UserOrganizationLink.objects
                .filter(user_id=user_id)
                .select_related("org")
                .filter(org__org_type=OrganizationType.COMPANY.value)
            )
            for link in companies:
                options.append({
                    "organiser_type": "company",
                    "label": link.org.title,
                    "entity_id": link.org_id,
                })

        return CustomResponse(response=options).get_success_response()


class CollaborationTargetsAPI(APIView):
    """
    GET events/meta/collaboration-targets/

    Returns searchable entities (IGs, campuses, companies) that can
    be invited as collaborators.
    """

    authentication_classes = [CustomizePermission]

    def get(self, request):
        search = request.query_params.get("search", "").strip()
        target_type = request.query_params.get("type", "").strip()
        targets = []

        # IGs
        if not target_type or target_type == "ig":
            igs = InterestGroup.objects.filter(status="active")
            if search:
                igs = igs.filter(name__icontains=search)
            for ig in igs[:20]:
                targets.append({
                    "collaborator_type": "ig",
                    "label": ig.name,
                    "ig_id": ig.id,
                })

        # Campuses (Colleges)
        if not target_type or target_type == "campus":
            campuses = Organization.objects.filter(
                org_type=OrganizationType.COLLEGE.value
            )
            if search:
                campuses = campuses.filter(title__icontains=search)
            for campus in campuses[:20]:
                targets.append({
                    "collaborator_type": "campus",
                    "label": campus.title,
                    "org_id": campus.id,
                })

        # Companies
        if not target_type or target_type == "company":
            companies = Organization.objects.filter(
                org_type=OrganizationType.COMPANY.value
            )
            if search:
                companies = companies.filter(title__icontains=search)
            for company in companies[:20]:
                targets.append({
                    "collaborator_type": "company",
                    "label": company.title,
                    "org_id": company.id,
                })

        return CustomResponse(response=targets).get_success_response()
