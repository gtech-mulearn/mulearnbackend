"""
Meta API views — helpers to populate form dropdowns.
"""
from rest_framework.views import APIView

from db.task import InterestGroup
from db.organization import Organization, UserOrganizationLink
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import RoleType


class OrganizerOptionsAPI(APIView):
    """
    GET /events/meta/organizer-options/
    Returns all organiser contexts the caller is authorised to create events as.
    Used to populate the "Create as…" dropdown in the event creation form.
    """
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        options = {
            'global_ig': [],      # IGs the user leads globally
            'campus_ig': [],      # Campus IG chapters the user leads (code present in roles)
            'campus': [],         # Campus orgs the user leads
            'company': [],        # Companies the user belongs to with Company role
            'admin': False,       # True if user is admin
        }

        # Admin can create events as admin
        if RoleType.ADMIN.value in roles:
            options['admin'] = True

        # Global IG leads: roles like "WEBDEV IGLead"
        ig_lead_codes = [
            r.replace(' IGLead', '')
            for r in roles if r.endswith(' IGLead')
        ]
        if ig_lead_codes:
            igs = InterestGroup.objects.filter(code__in=ig_lead_codes).values(
                'id', 'name', 'icon', 'code'
            )
            options['global_ig'] = list(igs)

        # Campus IG leads: roles like "WEBDEV CampusLead"
        ci_lead_codes = [
            r.replace(' CampusLead', '')
            for r in roles if r.endswith(' CampusLead')
        ]
        if ci_lead_codes:
            igs = InterestGroup.objects.filter(code__in=ci_lead_codes).values(
                'id', 'name', 'icon', 'code'
            )
            options['campus_ig'] = list(igs)

        # Campus Lead or Zonal/District leads can create campus events
        campus_lead_roles = {
            RoleType.CAMPUS_LEAD.value,
            RoleType.ZONAL_CAMPUS_LEAD.value,
            RoleType.DISTRICT_CAMPUS_LEAD.value,
        }
        if campus_lead_roles.intersection(set(roles)):
            user_orgs = UserOrganizationLink.objects.filter(
                user_id=user_id, verified=True
            ).select_related('org')
            for link in user_orgs:
                if link.org.org_type in ('College', 'School'):
                    options['campus'].append({
                        'id': link.org.id,
                        'title': link.org.title,
                        'org_type': link.org.org_type,
                    })

        # Company: user with Company role in a company org
        if RoleType.COMPANY.value in roles:
            user_orgs = UserOrganizationLink.objects.filter(
                user_id=user_id, verified=True
            ).select_related('org')
            for link in user_orgs:
                if link.org.org_type == 'Company':
                    options['company'].append({
                        'id': link.org.id,
                        'title': link.org.title,
                    })

        return CustomResponse(
            general_message='Organiser options retrieved.',
            response=options,
        ).get_success_response()


class CollaborationTargetsAPI(APIView):
    """
    GET /events/meta/collaboration-targets/?search=&type=
    Live search for entities that can be invited as collaborators.
    Used to power the collaborator search input.

    Query params:
      - search (str)  : partial name match
      - type   (str)  : ig | campus | campus_ig | company  (optional filter)
    """
    authentication_classes = [CustomizePermission]

    def get(self, request):
        search = request.query_params.get('search', '').strip()
        filter_type = request.query_params.get('type', '').strip()

        results = {
            'ig': [],
            'campus': [],
            'company': [],
        }

        if not filter_type or filter_type == 'ig':
            qs = InterestGroup.objects.all()
            if search:
                qs = qs.filter(name__icontains=search)
            results['ig'] = list(qs.values('id', 'name', 'icon', 'code')[:20])

        if not filter_type or filter_type == 'campus':
            qs = Organization.objects.filter(org_type='College')
            if search:
                qs = qs.filter(title__icontains=search)
            results['campus'] = list(qs.values('id', 'title', 'org_type')[:20])

        if not filter_type or filter_type == 'company':
            qs = Organization.objects.filter(org_type='Company')
            if search:
                qs = qs.filter(title__icontains=search)
            results['company'] = list(qs.values('id', 'title', 'org_type')[:20])

        return CustomResponse(
            general_message='Collaboration targets retrieved.',
            response=results,
        ).get_success_response()
