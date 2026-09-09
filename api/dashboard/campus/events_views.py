from collections import Counter

from django.db import transaction
from django.db.models import Q
from rest_framework.views import APIView

from db.organization import UserOrganizationLink
from db.events import Event
from db.user import User, Role, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils
from db.campus import CampusIGChapter, CampusExecomRole
from db.task import InterestGroup
import uuid
from . import serializers as campus_serializers
from .dash_campus_helper import (
    get_user_college_link,
    get_campus_events_qs,
    validate_campus_member,
    campus_staff_required,
    normalize_role_title,
    ig_synthetic_titles_for_org,
    match_ig_code_from_title,
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

        # Canonical form used for every privileged-role comparison below. The `role`
        # table uses a case-insensitive DB collation (utf8mb4_0900_ai_ci), so a plain
        # Python `==`/`in` check against the raw, attacker-supplied casing can be
        # bypassed (e.g. "campus lead") while the later DB lookup still resolves to
        # the real, privileged row. Casefold once and compare against that everywhere
        # — never against the raw `role_title`.
        canonical_role_title = " ".join(role_title.strip().split()).casefold()

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
        BLACKLIST_ROLES_CASEFOLD = {r.casefold() for r in BLACKLIST_ROLES}

        if canonical_role_title in BLACKLIST_ROLES_CASEFOLD:
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
            if role_title.startswith(f"{ig.code} ") or role_title.startswith(f"{ig.name} ") or role_title.startswith(f"{ig.code}_") or role_title.startswith(f"{ig.name}_") or role_title == f"{ig.code} CampusIGLead" or role_title == f"{ig.code}CampusIGLead":
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

        # Campus Lead has exactly one holder per campus and is reassigned only via
        # transfer-lead-role — never through this generic roster/assign flow.
        if canonical_role_title == RoleType.CAMPUS_LEAD.value.casefold():
            return CustomResponse(
                general_message="Campus Lead can't be assigned here. Use transfer-lead-role instead."
            ).get_failure_response()

        # role_title must already be a recognized execom role: either present in the
        # global campus_execom_role directory, an active IG-chapter-derived synthetic
        # title for this campus, or one of the always-assignable system roles below.
        # No auto-create here — create it via the roles directory first.
        #
        # Both the synthetic-title check and the always-assignable check compare
        # case-insensitively (via canonical_role_title), matching the catalog check's
        # title__iexact and the DB's own case-insensitive collation — a differently-cased
        # but otherwise valid title (e.g. "webdev campusiglead") must not be rejected while
        # "WEBDEV CampusIGLead" is accepted.
        ig_synthetic_titles_by_casefold = {
            title.casefold(): title for title in ig_synthetic_titles_for_org(org)
        }
        # Enabler and Lead Enabler are core system roles a Campus Lead must always be able
        # to grant from the campus dashboard, independent of whether the campus_execom_role
        # catalog has been seeded with them.
        ALWAYS_ASSIGNABLE_EXECOM_ROLES_BY_CASEFOLD = {
            RoleType.ENABLER.value.casefold(): RoleType.ENABLER.value,
            RoleType.LEAD_ENABLER.value.casefold(): RoleType.LEAD_ENABLER.value,
        }
        canonical_title_match = (
            ig_synthetic_titles_by_casefold.get(canonical_role_title)
            or ALWAYS_ASSIGNABLE_EXECOM_ROLES_BY_CASEFOLD.get(canonical_role_title)
        )

        if canonical_title_match is None and not CampusExecomRole.objects.filter(title__iexact=role_title).exists():
            return CustomResponse(
                general_message=f"'{role_title}' is not a recognized execom role. Create it in the role directory first."
            ).get_failure_response()

        # Normalize to the canonical casing so the chapter-field extraction below (which
        # does an exact-case suffix match) and the Role row we resolve/create below stay
        # consistent regardless of how the client cased the request.
        if canonical_title_match is not None:
            role_title = canonical_title_match

        # Wrap multi-table mutation in a single atomic transaction
        with transaction.atomic():
            # Fetch (or bridge-create) the matching system Role — UserRoleLink.role is a hard
            # FK to `role`, independent of the campus_execom_role directory above.
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

            # Assign new role — follows UserRoleLinkSerializer pattern
            serializer = campus_serializers.UserRoleLinkSerializer(
                data={"user": new_user.id, "role": role.id},
                context={"user_id": user_id},
            )
            if serializer.is_valid():
                serializer.save()

                ig_code_for_chapter_field = None
                chapter_field = None
                if role_title.endswith("CampusIGLead"):
                    ig_code_for_chapter_field = role_title[: -len("CampusIGLead")].strip()
                    chapter_field = "lead"
                elif role_title.endswith("CampusIGCoLead"):
                    ig_code_for_chapter_field = role_title[: -len("CampusIGCoLead")].strip()
                    chapter_field = "co_lead"

                if ig_code_for_chapter_field:
                    chapter = CampusIGChapter.objects.filter(
                        org=org, ig__code=ig_code_for_chapter_field, is_active=True
                    ).first()
                    if chapter:
                        setattr(chapter, chapter_field, new_user)
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

        ig_code_for_chapter_field = None
        chapter_field = None
        if role_title.endswith("CampusIGLead"):
            ig_code_for_chapter_field = role_title[: -len("CampusIGLead")].strip()
            chapter_field = "lead"
        elif role_title.endswith("CampusIGCoLead"):
            ig_code_for_chapter_field = role_title[: -len("CampusIGCoLead")].strip()
            chapter_field = "co_lead"

        if ig_code_for_chapter_field:
            chapter = CampusIGChapter.objects.filter(
                org=org, ig__code=ig_code_for_chapter_field, is_active=True
            ).first()
            if chapter and getattr(chapter, f"{chapter_field}_id") == user_id_of_role:
                setattr(chapter, chapter_field, None)
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

        # Per-campus IG-derived roles this org actually has active.
        this_campus_ig_titles = ig_synthetic_titles_for_org(org)

        # Global catalog, filtered so an IG-shaped title only shows for a campus that
        # actually has that IG active — otherwise it silently leaks another campus's roles.
        # "{code} IGLead" is never shown here at all — it's a plain, non-execom IG membership
        # role, not an assignable execom role, regardless of whether a legacy row for it exists.
        # "Campus Lead" is also never shown — it has exactly one holder per campus and must be
        # assigned only through transfer-lead-role, never through this generic roster picker.
        roles = set()
        for title in CampusExecomRole.objects.values_list("title", flat=True):
            if title.lower().endswith(" iglead") or title == RoleType.CAMPUS_LEAD.value:
                continue
            if match_ig_code_from_title(title) is None or title in this_campus_ig_titles:
                roles.add(title)

        roles.update(this_campus_ig_titles)

        # Enabler and Lead Enabler must always be offered as assignable roles from the
        # campus dashboard, independent of whether the campus_execom_role catalog has
        # been seeded with them — mirrors the always-assignable check in CampusExecomAPI.post.
        roles.add(RoleType.ENABLER.value)
        roles.add(RoleType.LEAD_ENABLER.value)

        return CustomResponse(response={"data": sorted(roles)}).get_success_response()


    @role_required([RoleType.CAMPUS_LEAD.value,RoleType.LEAD_ENABLER.value])
    @extend_schema(tags=['Dashboard - Campus'], description="Create Campus Execom Role.",
        responses={200: OpenApiResponse(description="Role created or already exists")},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        role_title = request.data.get("role_title")

        if not role_title:
            return CustomResponse(general_message="role_title is required").get_failure_response()

        # Normalize: strip extra whitespace
        role_title = " ".join(role_title.strip().split())

        blacklist = [
            RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.APPRAISER.value,
            RoleType.ZONAL_CAMPUS_LEAD.value, RoleType.DISTRICT_CAMPUS_LEAD.value,
            RoleType.MENTOR.value, RoleType.COMPANY.value, RoleType.BOT_DEV.value,
            RoleType.TECH_TEAM.value, RoleType.CAMPUS_ACTIVATION_TEAM.value,
            RoleType.DISCORD_MANAGER.value, RoleType.EX_OFFICIAL.value,
            RoleType.INTERN.value, RoleType.PRE_MEMBER.value, RoleType.SUSPEND.value,
            RoleType.MULEARNER.value
        ]

        if role_title.casefold() in {r.casefold() for r in blacklist}:
            return CustomResponse(general_message=f"Cannot create highly privileged system role: {role_title}").get_failure_response()

        if match_ig_code_from_title(role_title) is not None:
            return CustomResponse(
                general_message=f"'{role_title}' is an Interest-Group-specific role — it's managed automatically per campus and can't be added to the shared role directory."
            ).get_failure_response()

        # Atomic get-or-create: the title column has a case-insensitive unique
        # constraint, so a plain "check, then create" is racy — two concurrent
        # requests can both pass the check and then one hits an IntegrityError
        # on insert. get_or_create retries the lookup if create() raises that
        # IntegrityError, so the loser reuses the winner's row instead of 500ing.
        role, created = CampusExecomRole.objects.get_or_create(
            title=normalize_role_title(role_title),
            defaults={
                "id": str(uuid.uuid4()),
                "created_by_id": user_id,
                "updated_by_id": user_id,
            },
        )
        return CustomResponse(
            general_message="Role created successfully" if created else "Role already exists",
            response={"id": role.id, "title": role.title},
        ).get_success_response()


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
