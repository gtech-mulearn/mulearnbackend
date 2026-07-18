"""
Meta API views — helpers to populate form dropdowns.
"""
from rest_framework.views import APIView

from db.task import InterestGroup, Category
from db.events import Event
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
                'campus_context': s.DictField(allow_null=True),
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

        # Admin, Enabler, and Lead Enabler can create events as muLearn (admin organiser)
        if RoleType.ADMIN.value in roles or RoleType.ENABLER.value in roles or RoleType.LEAD_ENABLER.value in roles:
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

        # Company: user with Company role in a company org or UserMentor with COMPANY_MENTOR
        company_options = {}
        if RoleType.COMPANY.value in roles:
            user_orgs = UserOrganizationLink.objects.filter(
                user_id=user_id, verified=True
            ).select_related('org')
            for link in user_orgs:
                if link.org.org_type == 'Company':
                    company_options[link.org.id] = {
                        'id': link.org.id,
                        'title': link.org.title,
                    }
                    
        if RoleType.MENTOR.value in roles:
            from db.user import UserMentor
            from db.task import UserIgLink

            # Company Mentors → can create Company events for their org
            company_mentors = UserMentor.objects.filter(
                user_id=user_id,
                mentor_tier=UserMentor.MentorTier.COMPANY_MENTOR,
                status=UserMentor.Status.APPROVED,
            ).select_related('org')
            for mentor in company_mentors:
                if mentor.org:
                    company_options[mentor.org.id] = {
                        'id': mentor.org.id,
                        'title': mentor.org.title,
                    }

            # IG Mentors → can create Global IG events for their assigned IGs
            ig_mentor = UserMentor.objects.filter(
                user_id=user_id,
                mentor_tier=UserMentor.MentorTier.IG_MENTOR,
                status=UserMentor.Status.APPROVED,
            ).first()
            if ig_mentor:
                mentored_ig_ids = list(
                    UserIgLink.objects.filter(
                        user_id=user_id,
                        assignment_type=UserIgLink.AssignmentType.MENTOR,
                        is_active=True,
                    ).values_list('ig_id', flat=True)
                )
                if mentored_ig_ids:
                    mentored_igs = InterestGroup.objects.filter(
                        id__in=mentored_ig_ids
                    ).values('id', 'name', 'icon', 'code')
                    # Merge with existing ig options (avoid duplicates)
                    existing_ig_ids = {ig['id'] for ig in options['can_create_as_ig']}
                    for ig in mentored_igs:
                        if ig['id'] not in existing_ig_ids:
                            options['can_create_as_ig'].append(ig)

            # Campus Mentors → can create Campus IG events scoped to their campus
            campus_mentor = UserMentor.objects.filter(
                user_id=user_id,
                mentor_tier=UserMentor.MentorTier.CAMPUS_MENTOR,
                status=UserMentor.Status.APPROVED,
            ).select_related('org').first()
            if campus_mentor and campus_mentor.org:
                # Only IGs with an active chapter at the mentor's campus qualify
                # as campus_ig organiser options.
                campus_igs = InterestGroup.objects.filter(
                    campus_ig_chapter_ig__org_id=campus_mentor.org_id,
                    campus_ig_chapter_ig__is_active=True,
                ).distinct().values('id', 'name', 'icon', 'code')
                existing_ci_ids = {ig['id'] for ig in options['can_create_as_campus_ig']}
                for ig in campus_igs:
                    if ig['id'] not in existing_ci_ids:
                        options['can_create_as_campus_ig'].append(ig)

        options['can_create_as_company'] = list(company_options.values())

        # Resolve the creator's owning campus (for Campus-IG labelling on the FE).
        # Function-local import avoids a circular import with manage_views.
        from api.dashboard.events.manage_views import _resolve_creator_campus_id
        campus_id = _resolve_creator_campus_id(user_id)
        campus_context = None
        if campus_id:
            from db.organization import Organization
            campus_org = Organization.objects.filter(id=campus_id).first()
            if campus_org:
                campus_context = {'id': campus_org.id, 'title': campus_org.title}
        options['campus_context'] = campus_context

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
      - search    (str) : partial name match
      - type      (str) : ig | campus | campus_ig | company  (optional filter)
      - campus_id (str) : restrict campus_ig results to IGs with an active
                          chapter at this campus (used by the scope pickers;
                          collaborator search omits it and gets all IGs)
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

        campus_id = request.query_params.get('campus_id', '').strip()

        if not filter_type or filter_type in ('ig', 'campus_ig'):
            qs = InterestGroup.objects.all()
            if search:
                qs = qs.filter(name__icontains=search)
            if not filter_type or filter_type == 'ig':
                results['ig'] = list(qs.values('id', 'name', 'icon', 'code')[:20])
            if not filter_type or filter_type == 'campus_ig':
                # campus_ig entries are identified by their IG; return as campus_ig key.
                # When a campus context is given, only IGs with an active chapter
                # at that campus qualify — a campus with no chapters gets none.
                ci_qs = qs
                if campus_id:
                    ci_qs = ci_qs.filter(
                        campus_ig_chapter_ig__org_id=campus_id,
                        campus_ig_chapter_ig__is_active=True,
                    ).distinct()
                results['campus_ig'] = list(ci_qs.values('id', 'name', 'icon', 'code')[:20])

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


class EventTypesScopesAPI(APIView):
    """
    GET /events/meta/event-type-scope/
    Lists all valid event types and event scopes.
    No authentication required.
    """

    @extend_schema(tags=['Dashboard - Events'], description="Retrieve Event Types and Scopes.",
        responses={200: inline_serializer(
            name='EventTypesScopesResponse',
            fields={
                'event_type': s.ListField(child=s.CharField()),
                'event_scope': s.ListField(child=s.CharField()),
            }
        )},
    )
    def get(self, request):
        return CustomResponse(
            general_message='Event types and scopes retrieved.',
            response={
                "event_type": [
                    {"value": v, "label": l}
                    for v, l in zip(Event.EventType.values, Event.EventType.labels)
                ],
                "event_scope": [
                    {"value": v, "label": l}
                    for v, l in zip(Event.EventScope.values, Event.EventScope.labels)
                ],
            },
        ).get_success_response()

