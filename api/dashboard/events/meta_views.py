"""
Meta API views — helpers to populate form dropdowns.
"""
from rest_framework.views import APIView

from db.task import InterestGroup, Category
from db.organization import Organization, UserOrganizationLink
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import RoleType
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiResponse
from rest_framework import serializers as s


class EventCategoriesAPI(APIView):
    """
    GET /events/meta/categories/
    Lists all valid event categories for use in create/edit form dropdowns.
    No authentication required.
    """

    @extend_schema(tags=['Dashboard - Events'], description="Retrieve Event Categories.",
        responses={200: inline_serializer(
            name='EventCategoryItem',
            fields={
                'id': s.CharField(),
                'name': s.CharField(),
                'description': s.CharField(allow_null=True),
            },
            many=True,
        )},
    )
    def get(self, request):
        categories = Category.objects.filter(
            entity_type=Category.EntityType.EVENT,
        ).values('id', 'name', 'description').order_by('name')

        return CustomResponse(
            general_message='Event categories retrieved.',
            response=list(categories),
        ).get_success_response()


class OrganizerOptionsAPI(APIView):
    """
    GET /events/meta/organizer-options/
    Returns all organiser contexts the caller is authorised to create events as.
    Used to populate the "Create as…" dropdown in the event creation form.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Events'], description="Retrieve Organizer Options.",
        responses={200: inline_serializer(
            name='EventOrganizerOptions',
            fields={
                'can_create_as_ig': s.ListField(child=s.DictField()),
                'can_create_as_campus_ig': s.ListField(child=s.DictField()),
                'can_create_as_campus': s.ListField(child=s.DictField()),
                'can_create_as_company': s.ListField(child=s.DictField()),
                'can_create_as_admin': s.BooleanField(),
            },
        )},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        options = {
            'can_create_as_ig': [],      # IGs the user leads globally
            'can_create_as_campus_ig': [],      # Campus IG chapters the user leads (code present in roles)
            'can_create_as_campus': [],         # Campus orgs the user leads
            'can_create_as_company': [],        # Companies the user belongs to with Company role
            'can_create_as_admin': False,       # True if user is admin
        }

        # Admin can create events as admin
        if RoleType.ADMIN.value in roles:
            options['can_create_as_admin'] = True

        # Global IG leads: roles like "WEBDEV IGLead"
        ig_lead_codes = [
            r.replace(' IGLead', '')
            for r in roles if r.endswith(' IGLead')
        ]
        if ig_lead_codes:
            igs = InterestGroup.objects.filter(code__in=ig_lead_codes).values(
                'id', 'name', 'icon', 'code'
            )
            options['can_create_as_ig'] = list(igs)

        # Campus IG leads: roles like "WEBDEV CampusLead"
        ci_lead_codes = [
            r.replace(' CampusLead', '')
            for r in roles if r.endswith(' CampusLead')
        ]
        if ci_lead_codes:
            igs = InterestGroup.objects.filter(code__in=ci_lead_codes).values(
                'id', 'name', 'icon', 'code'
            )
            options['can_create_as_campus_ig'] = list(igs)

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
                    options['can_create_as_campus'].append({
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
                    options['can_create_as_company'].append({
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

    @extend_schema(tags=['Dashboard - Events'], description="Retrieve Collaboration Targets.",
        responses={200: inline_serializer(
            name='EventCollaborationTargets',
            fields={
                'ig': s.ListField(child=s.DictField()),
                'campus': s.ListField(child=s.DictField()),
                'company': s.ListField(child=s.DictField()),
                'campus_ig': s.ListField(child=s.DictField()),
            },
        )},
    )
    def get(self, request):
        search = request.query_params.get('search', '').strip()
        filter_type = request.query_params.get('type', '').strip()

        results = {
            'ig': [],
            'campus': [],
            'company': [],
            'campus_ig': [],
        }

        if not filter_type or filter_type in ('ig', 'campus_ig'):
            qs = InterestGroup.objects.all()
            if search:
                qs = qs.filter(name__icontains=search)
            ig_results = list(qs.values('id', 'name', 'icon', 'code')[:20])
            if not filter_type or filter_type == 'ig':
                results['ig'] = ig_results
            if not filter_type or filter_type == 'campus_ig':
                # campus_ig collaborators are identified by their IG; return as campus_ig key
                results['campus_ig'] = ig_results

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
