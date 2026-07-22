from collections import Counter

from django.db.models import Q
from rest_framework.views import APIView

from db.organization import UserOrganizationLink
from db.events import Event
from db.user import User, Role, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils
from db.campus import CampusIGChapter
from db.task import InterestGroup
import uuid
from . import serializers as campus_serializers
from .dash_campus_helper import (
    get_user_college_link,
    get_campus_events_qs,
    validate_campus_member,
    campus_staff_required,
)
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiResponse
from rest_framework import serializers as s


class CampusEventsAPI(APIView):
    """
    GET  campus/events/
    Returns paginated campus-scoped and campus-IG-scoped events
    for the authenticated campus lead's campus.
    """
    authentication_classes = [CustomizePermission]

    @campus_staff_required
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Retrieve Campus Events.",
        responses={200: campus_serializers.CampusEventListSerializer},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User has no organization"
            ).get_failure_response()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        org = user_org_link.org
        events = get_campus_events_qs(org)

        params = request.query_params

        if status := params.get("status"):
            events = events.filter(status=status)
        else:
            # Default view excludes unpublished drafts; pass ?status=draft to see them.
            events = events.exclude(status=Event.Status.DRAFT.value)

        if scope := params.get("scope"):
            events = events.filter(scope=scope)

        if event_type := params.get("event_type"):
            events = events.filter(organiser_type=event_type)

        if date_from := params.get("date_from"):
            events = events.filter(start_datetime__date__gte=date_from)

        if date_to := params.get("date_to"):
            events = events.filter(start_datetime__date__lte=date_to)

        paginated = CommonUtils.get_paginated_queryset(
            events,
            request,
            search_fields=["title"],
            sort_fields={
                "start_datetime": "start_datetime",
                "interest_count": "interest_count",
            },
        )

        serializer = campus_serializers.CampusEventListSerializer(
            paginated["queryset"], many=True
        )
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated["pagination"],
            }
        ).get_success_response()


class CampusEventDistributionAPI(APIView):
    """
    GET  campus/events/distribution/
    Returns ranked tag distribution for all campus events.
    Aggregates from Event.tags JSONField using Counter.
    """
    authentication_classes = [CustomizePermission]

    @campus_staff_required
    @extend_schema(tags=['Dashboard - Campus'], description="Retrieve Campus Event Distribution.",
        responses={200: inline_serializer(
            name="CampusEventDistributionResponse",
            fields={
                "hasError": s.BooleanField(),
                "statusCode": s.IntegerField(),
                "message": s.DictField(),
                "response": inline_serializer(
                    name="CampusEventDistributionData",
                    fields={
                        "data": inline_serializer(
                            name="CampusEventTagCount",
                            fields={
                                "tag": s.CharField(),
                                "event_count": s.IntegerField(),
                            },
                            many=True,
                        ),
                    },
                ),
            },
        )},
    )
    def get(self, request):

        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User has no organization"
            ).get_failure_response()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        org = user_org_link.org
        tags_qs = get_campus_events_qs(org).values_list("tags", flat=True)

        counter = Counter()
        for tags in tags_qs:
            if tags:  # tags is a JSONField, can be null
                counter.update(tags)

        data = [
            {"tag": tag, "event_count": count}
            for tag, count in counter.most_common()
        ]

        return CustomResponse(
            response={"data": data}
        ).get_success_response()


class CampusExecomAPI(APIView):
    """
    GET     campus/execom/              — list all execom role holders
    POST    campus/execom/              — appoint a member to a role
    DELETE  campus/execom/<member_id>/  — remove a role link
    """
    authentication_classes = [CustomizePermission]

    @campus_staff_required
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Retrieve Campus Execom.",
        responses={200: campus_serializers.ExecomMemberSerializer},
    )
    def get(self, request):

        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User has no organization"
            ).get_failure_response()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        org = user_org_link.org

        campus_user_ids = UserOrganizationLink.objects.filter(
            org=org,
            org__org_type=OrganizationType.COLLEGE.value,
            is_alumni=False,
        ).values_list("user_id", flat=True)

        execom_links = UserRoleLink.objects.filter(
            user_id__in=campus_user_ids,
            role__is_execom_role=True,
        ).select_related("user", "role")

        serializer = campus_serializers.ExecomMemberSerializer(
            execom_links, many=True
        )
        return CustomResponse(
            response={"data": serializer.data}
        ).get_success_response()

    @role_required([RoleType.CAMPUS_LEAD.value,RoleType.LEAD_ENABLER.value])
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Create Campus Execom.",
        request=campus_serializers.UserRoleLinkSerializer,
        responses={200: campus_serializers.ExecomMemberSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        muid = request.data.get("muid")
        role_title = request.data.get("role_title")

        if not muid or not role_title:
            return CustomResponse(
                general_message="muid and role_title are required"
            ).get_failure_response()

        # System roles that are highly privileged and cannot be assigned by campus leads
        BLACKLIST_ROLES = [
            RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.APPRAISER.value,
            RoleType.ZONAL_CAMPUS_LEAD.value, RoleType.DISTRICT_CAMPUS_LEAD.value,
            RoleType.MENTOR.value, RoleType.COMPANY.value, RoleType.BOT_DEV.value,
            RoleType.TECH_TEAM.value, RoleType.CAMPUS_ACTIVATION_TEAM.value,
            RoleType.DISCORD_MANAGER.value, RoleType.EX_OFFICIAL.value,
            RoleType.INTERN.value, RoleType.PRE_MEMBER.value, RoleType.SUSPEND.value,
            RoleType.MULEARNER.value
        ]
        
        if role_title in BLACKLIST_ROLES:
            return CustomResponse(
                general_message=f"Cannot assign highly privileged system role: {role_title}"
            ).get_failure_response()

        # Fetch user by muid
        new_user = User.objects.filter(muid=muid).first()
        if new_user is None:
            return CustomResponse(
                general_message="User not found"
            ).get_failure_response()

        # Get requester's campus
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User has no organization"
            ).get_failure_response()

        org = user_org_link.org
        if org is None:
            return CustomResponse(
                general_message="User has no organization"
            ).get_failure_response()

        # Validate IG if the role indicates one
        active_igs = CampusIGChapter.objects.filter(org=org, is_active=True).select_related("ig")
        matched_active_ig = False
        matched_inactive_or_missing_ig = False
        
        all_system_igs = InterestGroup.objects.all()
        for ig in all_system_igs:
            if role_title.startswith(f"{ig.code} ") or role_title.startswith(f"{ig.name} ") or role_title.startswith(f"{ig.code}_") or role_title.startswith(f"{ig.name}_") or role_title == f"{ig.code} CampusLead" or role_title == f"{ig.code}CampusLead":
                ig_active_in_campus = active_igs.filter(ig=ig).exists()
                if ig_active_in_campus:
                    matched_active_ig = True
                else:
                    matched_inactive_or_missing_ig = True

        if matched_inactive_or_missing_ig and not matched_active_ig:
            return CustomResponse(
                general_message="The Interest Group for this role is not active in your campus."
            ).get_failure_response()

        # Validate new user is a non-alumni campus member
        if not validate_campus_member(new_user.id, org.id):
            return CustomResponse(
                general_message="User is not a member of your campus"
            ).get_failure_response()

        # Fetch role by title
        role = Role.objects.filter(title=role_title).first()
        if role is not None and not role.is_execom_role:
            return CustomResponse(
                general_message=f"'{role_title}' is already in use by another feature and cannot be assigned as an execom role"
            ).get_failure_response()
        if role is None:
            role = Role.objects.create(
                id=str(uuid.uuid4()),
                title=role_title,
                created_by_id=user_id,
                updated_by_id=user_id,
                is_execom_role=True,
            )

        # Remove existing holder of this role in the campus
        campus_user_ids = UserOrganizationLink.objects.filter(
            org=org,
            org__org_type=OrganizationType.COLLEGE.value,
        ).values_list("user_id", flat=True)

        UserRoleLink.objects.filter(
            user_id__in=campus_user_ids,
            role=role,
        ).delete()

        # Assign new role — follows UserRoleLinkSerializer pattern
        serializer = campus_serializers.UserRoleLinkSerializer(
            data={"user": new_user.id, "role": role.id},
            context={"user_id": user_id},
        )
        if serializer.is_valid():
            serializer.save()

            if role_title.endswith("CampusLead") and role_title not in [RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value]:
                ig_code = role_title.replace("CampusLead", "").strip()
                chapter = CampusIGChapter.objects.filter(org=org, ig__code=ig_code, is_active=True).first()
                if chapter:
                    chapter.lead = new_user
                    chapter.updated_by_id = user_id
                    chapter.save()

            return CustomResponse(
                general_message="Role assigned successfully"
            ).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.CAMPUS_LEAD.value,RoleType.LEAD_ENABLER.value])
    @extend_schema(tags=['Dashboard - Campus'], description="Delete Campus Execom.",
        responses={200: campus_serializers.ExecomMemberSerializer},
    )

    def delete(self, request, member_id=None):
        user_id = JWTUtils.fetch_user_id(request)

        if not member_id:
            return CustomResponse(
                general_message="member_id is required"
            ).get_failure_response()

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User has no organization"
            ).get_failure_response()

        org = user_org_link.org

        if org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()
        # Fetch the role link
        role_link = UserRoleLink.objects.filter(
            id=member_id
        ).select_related("role").first()

        if role_link is None:
            return CustomResponse(
                general_message="Role link not found"
            ).get_failure_response()

        # Guard: must belong to this campus
        is_campus_member = UserOrganizationLink.objects.filter(
            org=org,
            org__org_type=OrganizationType.COLLEGE.value,
            user_id=role_link.user_id,
        ).exists()

        if not is_campus_member:
            return CustomResponse(
                general_message="Role link not found or not part of this campus"
            ).get_failure_response()

        # Guard: campus lead cannot remove their own lead role
        if (
            role_link.user_id == user_id
            and role_link.role.title == RoleType.CAMPUS_LEAD.value
        ):
            return CustomResponse(
                general_message="Cannot remove your own Campus Lead role. Use transfer-lead-role instead."
            ).get_failure_response()

        role_title = role_link.role.title
        user_id_of_role = role_link.user_id
        role_link.delete()

        if role_title.endswith("CampusLead") and role_title not in [RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value]:
            ig_code = role_title.replace("CampusLead", "").strip()
            chapter = CampusIGChapter.objects.filter(org=org, ig__code=ig_code, is_active=True).first()
            if chapter and chapter.lead_id == user_id_of_role:
                chapter.lead = None
                chapter.updated_by_id = user_id
                chapter.save()

        return CustomResponse(
            general_message="Role removed successfully"
        ).get_success_response()


class CampusExecomRoleAPI(APIView):
    """
    GET  campus/execom/roles/  — list all assignable roles
    POST campus/execom/roles/  — explicitly create a custom role
    """
    authentication_classes = [CustomizePermission]

    @campus_staff_required
    @extend_schema(tags=['Dashboard - Campus'], description="Retrieve Campus Execom Role.",
        responses={200: inline_serializer(
            name="CampusExecomRoleListResponse",
            fields={
                "hasError": s.BooleanField(),
                "statusCode": s.IntegerField(),
                "message": s.DictField(),
                "response": inline_serializer(
                    name="CampusExecomRoleListData",
                    fields={
                        "data": s.ListField(child=s.CharField()),
                    },
                ),
            },
        )},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(general_message="User has no organization").get_failure_response()

        org = user_org_link.org
        if org is None:
            return CustomResponse(general_message="Campus lead has no college").get_failure_response()

        roles = set()
        roles.add(RoleType.CAMPUS_LEAD.value)
        roles.add(RoleType.LEAD_ENABLER.value)
        roles.add(RoleType.ENABLER.value)
        roles.add(RoleType.IG_LEAD.value)
        

        # Active IG roles for this campus
        active_chapters = CampusIGChapter.objects.filter(org=org, is_active=True).select_related("ig")
        for chapter in active_chapters:
            if chapter.ig:
                roles.add(f"{chapter.ig.code} CampusLead")
                roles.add(f"{chapter.ig.code} IGLead")


        ig_campus_lead_titles = [
            RoleType.IG_CAMPUS_LEAD_ROLE(code)
            for code in InterestGroup.objects.values_list("code", flat=True)
        ]
        custom_execom_roles = Role.objects.filter(
            is_execom_role=True
        ).exclude(
            title__in=ig_campus_lead_titles
        ).values_list("title", flat=True)
        roles.update(custom_execom_roles)

        return CustomResponse(response={"data": sorted(list(roles))}).get_success_response()


    @role_required([RoleType.CAMPUS_LEAD.value,RoleType.LEAD_ENABLER.value])
    @extend_schema(tags=['Dashboard - Campus'], description="Create Campus Execom Role.",
        responses={200: OpenApiResponse(description="Role created or already exists")},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        role_title = request.data.get("role_title")

        if not role_title:
            return CustomResponse(general_message="role_title is required").get_failure_response()

        blacklist = [
            RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.APPRAISER.value,
            RoleType.ZONAL_CAMPUS_LEAD.value, RoleType.DISTRICT_CAMPUS_LEAD.value,
            RoleType.MENTOR.value, RoleType.COMPANY.value, RoleType.BOT_DEV.value,
            RoleType.TECH_TEAM.value, RoleType.CAMPUS_ACTIVATION_TEAM.value,
            RoleType.DISCORD_MANAGER.value, RoleType.EX_OFFICIAL.value,
            RoleType.INTERN.value, RoleType.PRE_MEMBER.value, RoleType.SUSPEND.value,
            RoleType.MULEARNER.value
        ]

        if role_title in blacklist:
            return CustomResponse(general_message=f"Cannot create highly privileged system role: {role_title}").get_failure_response()

        role = Role.objects.filter(title=role_title).first()
        if role:
            if not role.is_execom_role:
                return CustomResponse(
                    general_message=f"'{role_title}' is already in use by another feature and cannot be created as an execom role"
                ).get_failure_response()
            return CustomResponse(general_message="Role already exists").get_success_response()

        Role.objects.create(
            id=str(uuid.uuid4()),
            title=role_title,
            created_by_id=user_id,
            updated_by_id=user_id,
            is_execom_role=True,
        )

        return CustomResponse(general_message="Role created successfully").get_success_response()


class CampusUserSearchAPI(APIView):
    """
    GET  campus/execom/search/?q=<query>

    Searches campus members by full_name or muid (case-insensitive partial match).
    Returns all matching members regardless of whether they already hold an Execom
    role — this fixes the inconsistency where some existing Execom members were
    missing from search results because a plain exact-muid lookup was used.
    """
    authentication_classes = [CustomizePermission]

    @campus_staff_required
    @extend_schema(
        tags=['Dashboard - Campus'],
        description=(
            "Search campus members by name or muid. "
            "Returns all matching members including existing Execom role holders."
        ),
        responses={
            200: inline_serializer(
                name="CampusUserSearchResponse",
                fields={
                    "hasError": s.BooleanField(),
                    "statusCode": s.IntegerField(),
                    "message": s.DictField(),
                    "response": inline_serializer(
                        name="CampusUserSearchData",
                        fields={
                            "data": inline_serializer(
                                name="CampusUserSearchItem",
                                fields={
                                    "id": s.CharField(),
                                    "full_name": s.CharField(),
                                    "muid": s.CharField(),
                                    "profile_pic": s.CharField(allow_null=True),
                                },
                                many=True,
                            )
                        },
                    ),
                },
            )
        },
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User has no organization"
            ).get_failure_response()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        org = user_org_link.org
        query = request.query_params.get("q", "").strip()

        if not query:
            return CustomResponse(
                general_message="Query parameter 'q' is required"
            ).get_failure_response()

        # Fetch all active (non-alumni) member IDs for this campus
        campus_user_ids = UserOrganizationLink.objects.filter(
            org=org,
            org__org_type=OrganizationType.COLLEGE.value,
            is_alumni=False,
        ).values_list("user_id", flat=True)

        # Search by full_name OR muid — case-insensitive partial match.
        # Using User.objects (ActiveUserManager) so suspended users are excluded.
        users = User.objects.filter(
            id__in=campus_user_ids
        ).filter(
            Q(full_name__icontains=query) | Q(muid__icontains=query)
        ).order_by("full_name")[:20]

        data = [
            {
                "id": u.id,
                "full_name": u.full_name,
                "muid": u.muid,
                "profile_pic": u.profile_pic,
            }
            for u in users
        ]

        return CustomResponse(response={"data": data}).get_success_response()
