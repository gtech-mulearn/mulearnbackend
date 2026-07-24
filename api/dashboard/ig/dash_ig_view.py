from django.core.files.storage import FileSystemStorage
from django.db.models import Count
from rest_framework.views import APIView
from django.db import transaction
from db.task import InterestGroup
from db.user import User, Role
from utils.permission import CustomizePermission
from utils.permission import JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, WebHookActions, WebHookCategory
from utils.utils import CommonUtils, DiscordWebhooks
from .dash_ig_serializer import (
    InterestGroupSerializer,
    InterestGroupCreateUpdateSerializer,
    InterestGroupRequestSerializer,
    InterestGroupRequestGetSerializer,
)
import json
import uuid
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from api.dashboard.roles.dash_roles_serializer import RoleDashboardSerializer
from db.task import UserIgLink,UserIgLvlLink, Level
from db.user import Role, UserMentor, UserRoleLink
from utils.types import RoleType
from utils.utils import DateTimeUtils
from drf_spectacular.utils import extend_schema
from api.notification.notifications_utils import NotificationUtils


def _validate_muids(request_data, fields=("leads", "mentors")):
    """
    Validate that every muid in the given fields actually exists in the User table.
    Returns (is_valid, error_message).
    """
    for fld in fields:
        raw = request_data.get(fld)
        if not raw:
            continue
        # raw may already be a list (before json.dumps) or a string (already dumped)
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                continue
        if not isinstance(raw, list):
            continue

        muids = [
            item.get("muid")
            for item in raw
            if isinstance(item, dict) and item.get("muid")
        ]
        if not muids:
            continue

        existing = set(
            User.objects.filter(muid__in=muids).values_list("muid", flat=True)
        )
        invalid = [m for m in muids if m not in existing]
        if invalid:
            return False, f"Invalid MUIDs in '{fld}': {invalid}"

    return True, None


# " IGLead" — derived rather than hardcoded so it tracks IG_LEAD_ROLE().
_IG_LEAD_ROLE_SUFFIX = RoleType.IG_LEAD_ROLE("")


def _can_view_ig(roles):
    """
    Who may load a single Interest Group.

    Deliberately broader than _can_manage_ig: any IG lead can read any IG,
    so leads can reference how other groups are set up. Mirrors the frontend
    middleware, which admits any role ending in " IGLead".
    """
    return (
        RoleType.ADMIN.value in roles
        or RoleType.IG_LEAD.value in roles
        or any(role.endswith(_IG_LEAD_ROLE_SUFFIX) for role in roles)
    )


def _can_manage_ig(roles, ig):
    """
    Who may edit a single Interest Group.

    Admins and the platform-wide "IG Lead" role cover every IG; the dynamic
    "{code} IGLead" role covers only the IG it belongs to — an AI lead must
    not be able to edit the Web Development group.

    This cannot be expressed with @role_required, because the per-IG role
    title is only known once the IG has been loaded.
    """
    return (
        RoleType.ADMIN.value in roles
        or RoleType.IG_LEAD.value in roles
        or RoleType.IG_LEAD_ROLE(ig.code) in roles
    )


class InterestGroupImageAPI(APIView):
    """
    Upload/replace/remove an Interest Group's cover image or icon image.

    Mirrors the FileSystemStorage convention used for user profile cover
    pics (profile_view.UserProfileCoverView) and impact project images
    (impact_project_view.ImpactProjectImageAPI) — files live under
    MEDIA_ROOT, not as a DB column, keyed by the IG's id.

    `image_type` ("cover" or "icon") is bound per-URL via urls.py so the
    same view backs both <pk>/cover-image/ and <pk>/icon-image/.
    """
    authentication_classes = [CustomizePermission]

    MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

    def _path(self, image_type, pk):
        return f"interest_group/{image_type}/{pk}.png"

    def _field_name(self, image_type):
        return "cover_image" if image_type == "cover" else "icon_image"

    @extend_schema(
        tags=['Dashboard - Ig'],
        description="Upload or replace an Interest Group's cover/icon image.",
    )
    def post(self, request, pk, image_type):
        roles = JWTUtils.fetch_role(request)

        ig = InterestGroup.objects.filter(id=pk).first()
        if not ig:
            return CustomResponse(general_message="Interest Group Does Not Exist").get_failure_response()

        if not _can_manage_ig(roles, ig):
            return CustomResponse(
                general_message="You do not have permission to manage this Interest Group"
            ).get_failure_response()

        image = request.FILES.get("image")
        if image is None:
            return CustomResponse(general_message="No image provided").get_failure_response()

        if not image.content_type.startswith("image/"):
            return CustomResponse(general_message="Expected an image file").get_failure_response()

        if image.size > self.MAX_IMAGE_SIZE_BYTES:
            return CustomResponse(general_message="Image must be under 5 MB").get_failure_response()

        fs = FileSystemStorage()
        filename = self._path(image_type, ig.id)
        if fs.exists(filename):
            fs.delete(filename)
        fs.save(filename, image)

        return CustomResponse(
            response={self._field_name(image_type): getattr(ig, self._field_name(image_type))}
        ).get_success_response()

    @extend_schema(
        tags=['Dashboard - Ig'],
        description="Remove an Interest Group's cover/icon image.",
    )
    def delete(self, request, pk, image_type):
        roles = JWTUtils.fetch_role(request)

        ig = InterestGroup.objects.filter(id=pk).first()
        if not ig:
            return CustomResponse(general_message="Interest Group Does Not Exist").get_failure_response()

        if not _can_manage_ig(roles, ig):
            return CustomResponse(
                general_message="You do not have permission to manage this Interest Group"
            ).get_failure_response()

        fs = FileSystemStorage()
        filename = self._path(image_type, ig.id)
        if not fs.exists(filename):
            return CustomResponse(general_message="No image found").get_failure_response()

        fs.delete(filename)

        return CustomResponse(general_message="Image removed successfully").get_success_response()


class InterestGroupAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Ig'],
        description="Retrieve Interest Group.",
        responses={200: InterestGroupSerializer},
    )
    def get(self, request):
        ig_queryset = (
            InterestGroup.objects.select_related("created_by", "updated_by")
            .prefetch_related("user_ig_link_ig")
            .annotate(members=Count("user_ig_link_ig"))
            .all()
        )
        paginated_queryset = CommonUtils.get_paginated_queryset(
            ig_queryset,
            request,
            [
                "name",
                "created_by__full_name",
                "updated_by__full_name",
            ],
            {
                "name": "name",
                "members": "members",
                "status": "status",
                "updated_on": "updated_at",
                "updated_by": "updated_by__full_name",
                "created_on": "created_at",
                "created_by": "created_by__full_name",
            },
        )

        ig_serializer_data = InterestGroupSerializer(
            paginated_queryset.get("queryset"), many=True
        ).data

        return CustomResponse().paginated_response(
            data=ig_serializer_data, pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Ig'],
        description="Create Interest Group.",
        request=InterestGroupCreateUpdateSerializer,
        responses={200: RoleDashboardSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        request_data = request.data

        # Validate MUIDs for leads/mentors before serializing
        is_valid, error_msg = _validate_muids(request_data)
        if not is_valid:
            return CustomResponse(general_message=error_msg).get_failure_response()

        # serialize JSON-able fields to strings for DB storage
        for fld in [
            "prerequisites",
            "career_opportunities",
            "top_blogs",
            "people_to_follow",
            "leads",
            "mentors",
        ]:
            if fld in request_data and not isinstance(request_data.get(fld), str):
                try:
                    request_data[fld] = json.dumps(request_data.get(fld))
                except Exception:
                    pass

        request_data["created_by"] = request_data["updated_by"] = user_id

        serializer = InterestGroupCreateUpdateSerializer(
            data=request_data,
        )

        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()

                ig_name = request_data.get("name")
                ig_code = request_data.get("code")

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
                            "created_by_id": request_data.get("created_by"),
                            "updated_by_id": request_data.get("updated_by"),
                            "is_execom_role": role_data["is_execom_role"],
                        }
                    )

            DiscordWebhooks.general_updates(
                WebHookCategory.INTEREST_GROUP.value,
                WebHookActions.CREATE.value,
                request_data.get("name"),
                request_data.get("code"),
            )

            return CustomResponse(
                response={"interestGroup": serializer.data}
            ).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value,RoleType.IG_LEAD.value])
    @extend_schema(
        tags=['Dashboard - Ig'],
        description="Update Interest Group.",
        request=InterestGroupCreateUpdateSerializer,
        responses={200: InterestGroupSerializer},
    )
    def put(self, request, pk):
        user_id = JWTUtils.fetch_user_id(request)
        ig = InterestGroup.objects.get(id=pk)

        ig_old_name = ig.name
        ig_old_code = ig.code

        request_data = request.data

        # Validate MUIDs for leads/mentors before serializing
        is_valid, error_msg = _validate_muids(request_data)
        if not is_valid:
            return CustomResponse(general_message=error_msg).get_failure_response()

        for fld in [
            "prerequisites",
            "career_opportunities",
            "top_blogs",
            "people_to_follow",
            "leads",
            "mentors",
        ]:
            if fld in request_data and not isinstance(request_data.get(fld), str):
                try:
                    request_data[fld] = json.dumps(request_data.get(fld))
                except Exception:
                    pass
        request_data["updated_by"] = user_id

        serializer = InterestGroupCreateUpdateSerializer(
            data=request_data, instance=ig, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            ig_new_name = ig.name
            ig_new_code = ig.code

            ig_role = Role.objects.filter(title=ig_old_name).first()

            if ig_role:
                ig_role.title = ig_new_name
                ig_role.description = ig_new_name + " Interest Group Member"
                ig_role.save()

            ig_campus_lead_role = Role.objects.filter(
                title=RoleType.IG_CAMPUS_LEAD_ROLE(ig_old_code)
            ).first()

            if ig_campus_lead_role:
                ig_campus_lead_role.title = ig_new_code + " CampusLead"
                ig_campus_lead_role.description = (
                    ig_new_name + " Interest Group Campus Lead"
                )
                ig_campus_lead_role.save()

            ig_lead_role = Role.objects.filter(
                title=RoleType.IG_LEAD_ROLE(ig_old_code)
            ).first()

            if ig_lead_role:
                ig_lead_role.title = RoleType.IG_LEAD_ROLE(ig_new_code)
                ig_lead_role.description = ig_new_name + " Interest Group Lead"
                ig_lead_role.save()

            DiscordWebhooks.general_updates(
                WebHookCategory.INTEREST_GROUP.value,
                WebHookActions.EDIT.value,
                ig_new_name,
                ig_new_code,
                ig_old_name,
                ig_old_code,
            )
            return CustomResponse(
                response={"interestGroup": serializer.data}
            ).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(tags=['Dashboard - Ig'], description="Delete Interest Group.",
        responses={200: InterestGroupSerializer},
    )
    def delete(self, request, pk):
        ig = InterestGroup.objects.filter(id=pk).first()

        if ig is None:
            return CustomResponse(general_message="invalid ig").get_success_response()
        ig_role = Role.objects.filter(title=ig.name).first()
        if ig_role:
            ig_role.delete()
        ig_campus_role = Role.objects.filter(
            title=RoleType.IG_CAMPUS_LEAD_ROLE(ig.code)
        ).first()
        if ig_campus_role:
            ig_campus_role.delete()
        ig_lead_role = Role.objects.filter(title=RoleType.IG_LEAD_ROLE(ig.code)).first()
        if ig_lead_role:
            ig_lead_role.delete()
        ig.delete()

        DiscordWebhooks.general_updates(
            WebHookCategory.INTEREST_GROUP.value,
            WebHookActions.DELETE.value,
            ig.name,
            ig.code,
        )
        return CustomResponse(
            general_message="ig deleted successfully"
        ).get_success_response()


class InterestGroupCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Ig'],
        description="Retrieve Interest Group C S V.",
        responses={200: InterestGroupSerializer},
    )
    def get(self, request):
        ig_serializer = (
            InterestGroup.objects.select_related("created_by", "updated_by")
            .prefetch_related("user_ig_link_ig")
            .annotate(members=Count("user_ig_link_ig"))
            .all()
        )

        ig_serializer_data = InterestGroupSerializer(ig_serializer, many=True).data

        return CommonUtils.generate_csv(ig_serializer_data, "Interest Group")


class InterestGroupGetAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Ig'],
        description="Retrieve Interest Group Get.",
        responses={200: InterestGroupSerializer},
    )
    def get(self, request, pk):
        """Allow Admin or any IG lead to load the IG."""
        roles = JWTUtils.fetch_role(request)
        ig_data = InterestGroup.objects.filter(id=pk).first()

        if not ig_data:
            return CustomResponse(
                general_message="Interest Group Does Not Exist"
            ).get_failure_response()

        if not _can_view_ig(roles):
            return CustomResponse(
                general_message="You do not have permission to view this Interest Group"
            ).get_failure_response()

        serializer = InterestGroupSerializer(ig_data, many=False)

        return CustomResponse(
            response={"interestGroup": serializer.data}
        ).get_success_response()

    @extend_schema(
        tags=['Dashboard - Ig'],
        description="Partially update Interest Group Get.",
        request=InterestGroupCreateUpdateSerializer,
        responses={200: InterestGroupSerializer},
    )
    def patch(self, request, pk):
        """Allow IG Lead or Admin to update IG editable fields."""
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        ig = InterestGroup.objects.filter(id=pk).first()
        if not ig:
            return CustomResponse(general_message="Interest Group Does Not Exist").get_failure_response()

        if not _can_manage_ig(roles, ig):
            return CustomResponse(general_message="You do not have permission to update this Interest Group").get_failure_response()

        request_data = request.data

        # Validate MUIDs for leads/mentors before serializing
        is_valid, error_msg = _validate_muids(request_data)
        if not is_valid:
            return CustomResponse(general_message=error_msg).get_failure_response()

        for fld in [
            "prerequisites",
            "career_opportunities",
            "top_blogs",
            "people_to_follow",
            "leads",
            "mentors",
        ]:
            if fld in request_data and not isinstance(request_data.get(fld), str):
                try:
                    request_data[fld] = json.dumps(request_data.get(fld))
                except Exception:
                    pass
        request_data["updated_by"] = user_id

        serializer = InterestGroupCreateUpdateSerializer(data=request_data, instance=ig, partial=True)

        if serializer.is_valid():
            serializer.save()

            # ── Side-effect: sync the per-IG lead role with the leads list ──────
            # Without this the Leads field is cosmetic: the muids are stored on
            # the IG row, but the user never receives "{code} IGLead" and so
            # cannot edit the IG they were just made lead of.
            #
            # When "leads" is present it is treated as the COMPLETE set of leads
            # for this IG — anyone dropped from it loses the role. A payload
            # without the key leaves lead roles untouched, so unrelated partial
            # updates are safe. The frontend only sends "leads" when it changed.
            if "leads" in request.data:
                raw_leads = request.data.get("leads")
                if isinstance(raw_leads, str):
                    try:
                        raw_leads = json.loads(raw_leads)
                    except Exception:
                        raw_leads = []
                if not isinstance(raw_leads, list):
                    raw_leads = []

                lead_role, _ = Role.objects.get_or_create(
                    title=RoleType.IG_LEAD_ROLE(ig.code),
                    defaults={
                        "id": str(uuid.uuid4()),
                        "description": f"{ig.name} Interest Group Lead",
                        "created_by_id": user_id,
                        "updated_by_id": user_id,
                    },
                )

                desired_lead_muids = {
                    (item.get("muid") if isinstance(item, dict) else item)
                    for item in raw_leads
                }
                desired_lead_muids.discard(None)
                desired_lead_muids.discard("")

                # Revoke first, so a lead moved out of the list loses access even
                # if their replacement's muid turns out to be invalid. Deleted
                # rather than deactivated to match the role-transfer logic in
                # dash_campus_helper.assign_ig_campus_lead().
                UserRoleLink.objects.filter(role=lead_role).exclude(
                    user__muid__in=desired_lead_muids
                ).delete()

                for muid in desired_lead_muids:
                    target_user = User.objects.filter(muid=muid).first()
                    if not target_user:
                        continue

                    _, lead_link_created = UserRoleLink.objects.get_or_create(
                        user=target_user,
                        role=lead_role,
                        defaults={"verified": True, "created_by_id": user_id},
                    )

                    if lead_link_created:
                        caller = User.objects.filter(id=user_id).first()
                        caller_name = caller.full_name if caller else "An admin"
                        NotificationUtils.insert_notification(
                            user=target_user,
                            title=f"IG Lead: {ig.name}"[:50],
                            description=(
                                f"{caller_name} has assigned you as a Lead for "
                                f"{ig.name}. You can now edit this interest group."
                            )[:200],
                            button='View',
                            url=f'/interest-groups/{ig.id}/',
                            created_by=caller,
                        )

            # ── Side-effect: assign Mentor role + UserIgLink for new mentors ────
            raw_mentors = request.data.get("mentors")
            if raw_mentors:
                if isinstance(raw_mentors, str):
                    try:
                        raw_mentors = json.loads(raw_mentors)
                    except Exception:
                        raw_mentors = []

                mentor_role = Role.objects.filter(title=RoleType.MENTOR.value).first()
                for item in (raw_mentors or []):
                    muid = item.get("muid") if isinstance(item, dict) else item
                    if not muid:
                        continue
                    target_user = User.objects.filter(muid=muid).first()
                    if not target_user:
                        continue

                    # 1. Ensure an approved UserMentor profile exists.
                    # Never overwrite mentor_tier on an existing profile —
                    # a Company/Campus mentor gaining IG-mentor authority is
                    # additive (via the MentorScopeGrant below), not a tier
                    # replacement.
                    now = DateTimeUtils.get_current_utc_time()
                    mentor_profile, created = UserMentor.objects.get_or_create(
                        user=target_user,
                        defaults={
                            "status":        UserMentor.Status.APPROVED,
                            "mentor_tier":   UserMentor.MentorTier.IG_MENTOR,
                            "verified_by_id": user_id,
                            "verified_at":   now,
                            "created_by_id": user_id,
                            "updated_by_id": user_id,
                            "created_at":    now,
                            "updated_at":    now,
                        },
                    )
                    if not created and mentor_profile.status != UserMentor.Status.APPROVED:
                        mentor_profile.status = UserMentor.Status.APPROVED
                        mentor_profile.verified_by_id = user_id
                        mentor_profile.verified_at = now
                        mentor_profile.updated_by_id = user_id
                        mentor_profile.updated_at = now
                        mentor_profile.save(update_fields=[
                            "status", "verified_by_id", "verified_at",
                            "updated_by_id", "updated_at",
                        ])

                    # 1b. Grant IG-scoped authority additively.
                    from db.user import MentorScopeGrant
                    grant, grant_created = MentorScopeGrant.objects.get_or_create(
                        mentor=mentor_profile,
                        scope_type=MentorScopeGrant.ScopeType.IG_MENTOR,
                        scope_id=str(ig.id),
                        defaults={
                            "is_active":     True,
                            "granted_by_id": user_id,
                            "granted_at":    now,
                        },
                    )
                    if not grant_created and not grant.is_active:
                        grant.is_active = True
                        grant.revoked_by = None
                        grant.revoked_at = None
                        grant.save(update_fields=["is_active", "revoked_by", "revoked_at"])

                    # 2. Assign Mentor role (idempotent)
                    if mentor_role:
                        UserRoleLink.objects.get_or_create(
                            user=target_user,
                            role=mentor_role,
                            defaults={"verified": True, "created_by_id": user_id},
                        )

                    # 3. Create active UserIgLink (idempotent)
                    link, link_created = UserIgLink.objects.get_or_create(
                        user=target_user,
                        ig=ig,
                        assignment_type=UserIgLink.AssignmentType.MENTOR,
                        defaults={
                            "is_active":      True,
                            "assigned_by_id": user_id,
                            "created_by_id":  user_id,
                        },
                    )
                    if not link_created and not link.is_active:
                        link.is_active = True
                        link.assigned_by_id = user_id
                        link.save()

                    # 4. Notify the newly assigned mentor
                    if created or grant_created or link_created:
                        caller = User.objects.filter(id=user_id).first()
                        caller_name = caller.full_name if caller else "An IG Lead"
                        NotificationUtils.insert_notification(
                            user=target_user,
                            title=f"IG Mentor: {ig.name}"[:50],
                            description=(
                                f"{caller_name} has assigned you as an IG Mentor for "
                                f"{ig.name}. You can now create sessions and manage "
                                f"tasks within this interest group."
                            )[:200],
                            button='View',
                            url=f'/interest-groups/{ig.id}/',
                            created_by=caller,
                        )

            return CustomResponse(response={"interestGroup": serializer.data}).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()


class InterestGroupRequestAPI(APIView):
    """API endpoint for users to submit and retrieve IG creation requests."""
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, RoleType.COMPANY.value])
    @extend_schema(
        tags=['Dashboard - Ig'],
        description="Retrieve Interest Group Request.",
        responses={200: InterestGroupRequestGetSerializer},
    )
    def get(self, request):
        """Retrieve Interest Group requests created by a company user.
        
        Query Parameters:
            - user_id (optional): Filter by specific company user ID. 
              If not provided, defaults to the authenticated user's ID.
              Only admins can query other users' requests.
            - status (optional): Filter by IG status (requested, active, rejected, cancelled)
        """
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        target_user_id = request.query_params.get('user_id')
        status_filter = request.query_params.get('status')
        is_admin = RoleType.ADMIN.value in roles

        ig_queryset = InterestGroup.objects.select_related(
            "created_by", "updated_by"
        ).prefetch_related(
            "user_ig_link_ig",
            "created_by__user_role_link_user__role",
            "created_by__user_organization_link_user__org"
        )
        
        if target_user_id:
            if target_user_id != user_id and not is_admin:
                return CustomResponse(
                    general_message="You can only view your own IG requests"
                ).get_failure_response()
            ig_queryset = ig_queryset.filter(created_by_id=target_user_id)
        else:
            if not is_admin:
                ig_queryset = ig_queryset.filter(created_by_id=user_id)

        if status_filter:
            valid_statuses = ['active', 'requested', 'cancelled', 'rejected']
            if status_filter not in valid_statuses:
                return CustomResponse(
                    general_message=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                ).get_failure_response()
            ig_queryset = ig_queryset.filter(status=status_filter)
        else:
            # Default ("All") view excludes cancelled requests; use ?status=cancelled to see them.
            ig_queryset = ig_queryset.exclude(status='cancelled')

        paginated_queryset = CommonUtils.get_paginated_queryset(
            ig_queryset,
            request,
            ["name", "code", "category"],
            {
                "name": "name",
                "status": "status",
                "ig_name": "name",
                "user_full_name": "created_by__full_name",
                "created_at": "created_at",
                "created_on": "created_at",
                "updated_on": "updated_at",
            },
        )

        ig_serializer_data = InterestGroupRequestGetSerializer(
            paginated_queryset.get("queryset"), many=True
        ).data
        
        return CustomResponse().paginated_response(
            data=ig_serializer_data, 
            pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value, RoleType.COMPANY.value])
    @extend_schema(
        tags=['Dashboard - Ig'],
        description="Create Interest Group Request.",
        request=InterestGroupRequestSerializer,
        responses={200: InterestGroupSerializer},
    )
    def post(self, request):
        """Submit a new Interest Group creation request."""
        user_id = JWTUtils.fetch_user_id(request)

        request_data = request.data.copy()

        # Validate MUIDs for leads/mentors before serializing
        is_valid, error_msg = _validate_muids(request_data)
        if not is_valid:
            return CustomResponse(general_message=error_msg).get_failure_response()

        for fld in [
            "prerequisites",
            "career_opportunities",
            "top_blogs",
            "people_to_follow",
            "leads",
            "mentors",
        ]:
            if fld in request_data and not isinstance(request_data.get(fld), str):
                try:
                    request_data[fld] = json.dumps(request_data.get(fld))
                except Exception:
                    pass

        serializer = InterestGroupRequestSerializer(data=request_data)

        if serializer.is_valid():
            ig_instance = serializer.save(
                created_by_id=user_id,
                updated_by_id=user_id,
                status="requested"
            )
            response_serializer = InterestGroupSerializer(ig_instance)
            
            return CustomResponse(
                response={"interestGroup": response_serializer.data},
                general_message="Interest Group request submitted successfully. It will be reviewed by admins."
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Ig'],
        description="Partially update Interest Group Request.",
        responses={200: InterestGroupSerializer},
    )
    def patch(self, request, pk):
        """Update Interest Group request status (Admin only).
        
        Allowed status transitions:
            - requested → active
            - requested → rejected
            - requested → cancelled
            - any status → any status (admin override)
        """
        user_id = JWTUtils.fetch_user_id(request)
        
        try:
            ig = InterestGroup.objects.get(id=pk)
        except InterestGroup.DoesNotExist:
            return CustomResponse(
                general_message="Interest Group not found"
            ).get_failure_response()

        new_status = request.data.get('status')

        valid_statuses = ['active', 'requested', 'cancelled', 'rejected']
        if not new_status:
            return CustomResponse(
                general_message="Status field is required"
            ).get_failure_response()
        
        if new_status not in valid_statuses:
            return CustomResponse(
                general_message=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            ).get_failure_response()

        ig.status = new_status
        ig.updated_by_id = user_id
        ig.save()

        # Notify the original requester
        actor = User.objects.filter(id=user_id).first()
        requester = ig.created_by
        if actor and requester and str(requester.id) != user_id:
            if new_status == 'active':
                NotificationUtils.insert_notification(
                    user=requester,
                    title='Interest Group Approved',
                    description=f'Your Interest Group request "{ig.name}" has been approved and is now active!',
                    button='View',
                    url=f'/interest-groups/{ig.id}/',
                    created_by=actor,
                )
            elif new_status == 'rejected':
                NotificationUtils.insert_notification(
                    user=requester,
                    title='Interest Group Rejected',
                    description=f'Your Interest Group request "{ig.name}" has been rejected.',
                    button=None,
                    url=None,
                    created_by=actor,
                )

        response_serializer = InterestGroupSerializer(ig)
        
        return CustomResponse(
            response={"interestGroup": response_serializer.data},
            general_message=f"Interest Group status updated to '{new_status}'"
        ).get_success_response()

    @role_required([RoleType.ADMIN.value, RoleType.COMPANY.value])
    @extend_schema(
        tags=['Dashboard - Ig'],
        description=(
            "Cancel an IG creation request. "
            "Company users can only cancel their own requests that are still in 'requested' status. "
            "Admins can cancel any request regardless of status or owner."
        ),
        responses={200: InterestGroupSerializer},
    )
    def delete(self, request, pk):
        """Cancel an IG creation request.

        - Company users: can cancel only their own request, only when status='requested'.
        - Admins: can cancel any request at any status.
        """
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        is_admin = RoleType.ADMIN.value in roles

        try:
            ig = InterestGroup.objects.get(id=pk)
        except InterestGroup.DoesNotExist:
            return CustomResponse(
                general_message="Interest Group request not found."
            ).get_failure_response()

        # Ownership check for non-admins
        if not is_admin and str(ig.created_by_id) != str(user_id):
            return CustomResponse(
                general_message="You can only cancel your own IG requests."
            ).get_failure_response()

        # Status check for non-admins — only 'requested' can be cancelled by the requester
        if not is_admin and ig.status != 'requested':
            return CustomResponse(
                general_message=f"Cannot cancel a request that is already '{ig.status}'. Only 'requested' status can be cancelled."
            ).get_failure_response()

        ig.status = 'cancelled'
        ig.updated_by_id = user_id
        ig.save()

        return CustomResponse(
            general_message="Interest Group request cancelled successfully."
        ).get_success_response()


class InterestGroupListApi(APIView):
    @method_decorator(cache_page(60 * 10))
    @extend_schema(
        tags=['Dashboard - Ig'],
        description="Retrieve Interest Group List Api.",
        responses={200: InterestGroupSerializer},
    )
    def get(self, request):
        ig = (
            InterestGroup.objects.all()
            .select_related("created_by", "updated_by")
            .prefetch_related("user_ig_link_ig")
            .annotate(members=Count("user_ig_link_ig"))
        )

        serializer = InterestGroupSerializer(ig, many=True)

        return CustomResponse(
            response={"interestGroup": serializer.data}
        ).get_success_response()

class InterestGroupMembershipAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Ig'],
        description="Join Interest Group instantly.",
        responses={200: InterestGroupSerializer},
    )
    def post(self, request, pk):
        user_id = JWTUtils.fetch_user_id(request)

        ig = InterestGroup.objects.filter(id=pk, status='active').first()
        if not ig:
            return CustomResponse(general_message="Interest Group not found or inactive").get_failure_response()

        with transaction.atomic():
            existing_link = UserIgLink.objects.filter(
                user_id=user_id,
                ig_id=pk,
                assignment_type=UserIgLink.AssignmentType.LEARNER
            ).first()

            if existing_link and existing_link.is_active:
                return CustomResponse(general_message="Already joined this Interest Group").get_success_response()

            active_learner_ig_count = UserIgLink.objects.filter(
                user_id=user_id,
                assignment_type=UserIgLink.AssignmentType.LEARNER,
                is_active=True
            ).count()

            # enforce max 3 selected learner IGs
            if not existing_link and active_learner_ig_count >= 3:
                return CustomResponse(general_message="Cannot join more than 3 interest groups").get_failure_response()

            if existing_link:
                existing_link.is_active = True
                existing_link.unassigned_at = None
                existing_link.assigned_by_id = user_id
                existing_link.save(update_fields=["is_active", "unassigned_at", "assigned_by"])
            else:
                UserIgLink.objects.create(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    ig_id=pk,
                    assignment_type=UserIgLink.AssignmentType.LEARNER,
                    is_active=True,
                    assigned_by_id=user_id,
                    created_by_id=user_id,
                )

            # ensure level-1 IG link exists
            level_1 = Level.objects.filter(level_order=1).first()
            if level_1:
                UserIgLvlLink.objects.get_or_create(
                    user_id=user_id,
                    ig_id=pk,
                    defaults={
                        "id": uuid.uuid4(),
                        "level_id": level_1.id,
                        "created_by_id": user_id,
                        "updated_by_id": user_id,
                    },
                )

        return CustomResponse(general_message="Joined Interest Group successfully").get_success_response()

    @extend_schema(
        tags=['Dashboard - Ig'],
        description="Leave Interest Group instantly.",
        responses={200: InterestGroupSerializer},
    )
    def delete(self, request, pk):
        user_id = JWTUtils.fetch_user_id(request)

        link = UserIgLink.objects.filter(
            user_id=user_id,
            ig_id=pk,
            assignment_type=UserIgLink.AssignmentType.LEARNER
        ).first()

        if not link or not link.is_active:
            return CustomResponse(general_message="Already left this Interest Group").get_success_response()

        link.is_active = False
        link.unassigned_at = DateTimeUtils.get_current_utc_time()
        link.save(update_fields=["is_active", "unassigned_at"])

       
        return CustomResponse(general_message="Left Interest Group successfully").get_success_response()