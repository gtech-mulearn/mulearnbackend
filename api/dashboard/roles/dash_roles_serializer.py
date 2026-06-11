import uuid

from rest_framework import serializers

from db.user import Role, User, UserRoleLink, UserMentor
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils, DiscordWebhooks
from utils.types import WebHookActions, WebHookCategory, RoleType, InternGuild
from django.db.models import Q
from django.db import transaction


class UserRoleLinkManagementSerializer(serializers.ModelSerializer):
    """
    Serializer used by UserRoleLinkManagement API to lists the
    details of the user with a specific role
    """

    class Meta:
        model = User
        fields = ["id", "muid", "full_name"]


class RoleAssignmentSerializer(serializers.Serializer):
    """
    Used by UserRoleLinkManagement to assign
    a role to a large number of users
    """

    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all())
    users = serializers.ListField(child=serializers.UUIDField())
    created_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    def validate(self, attrs):
        data = super().validate(attrs)
        attrs = set(attrs["users"])
        users = User.objects.filter(
            ~Q(user_role_link_user__role=data["role"]), pk__in=attrs
        )
        if users.count() != len(attrs):
            raise serializers.ValidationError("One or more user IDs are invalid.")

        data["users"] = users
        return data

    def create(self, validated_data):
        users = validated_data.pop("users")
        validated_data["created_at"] = DateTimeUtils.get_current_utc_time()
        validated_data["verified"] = True
        user_roles_to_create = [
            UserRoleLink(user=user, **validated_data) for user in users
        ]
        with transaction.atomic():
            UserRoleLink.objects.bulk_create(user_roles_to_create)
            DiscordWebhooks.general_updates(
                WebHookCategory.BULK_ROLE.value,
                WebHookActions.UPDATE.value,
                validated_data["role"].title,
                ",".join(list(users.values_list("id", flat=True))),
            )
        return user_roles_to_create, validated_data["role"]


class RoleDashboardSerializer(serializers.ModelSerializer):
    updated_by = serializers.CharField(source="updated_by.full_name")
    created_by = serializers.CharField(source="created_by.full_name")
    members = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_at",
            "created_by",
            "updated_by",
            "updated_at",
            "members",
        ]

    def get_members(self, obj):
        return len(UserRoleLink.objects.filter(role_id=obj.id, verified=True))

    def update(self, instance, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context["request"])
        user = User.objects.get(id=user_id)

        validated_data["updated_by"] = user
        validated_data["updated_at"] = DateTimeUtils.get_current_utc_time()

        return super().update(instance, validated_data)

    def create(self, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context["request"])
        user = User.objects.get(id=user_id)

        validated_data["id"] = uuid.uuid4()
        validated_data["created_by"] = validated_data["updated_by"] = user
        validated_data["created_at"] = validated_data[
            "updated_at"
        ] = DateTimeUtils.get_current_utc_time()

        return super().create(validated_data)


class UserRoleSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "full_name", "muid"]


class UserRoleCreateSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(required=True, source="user.id")
    role_id = serializers.CharField(required=True, source="role.id")
    # Required when assigning the Intern role.
    guild = serializers.ChoiceField(
        choices=InternGuild.get_all_values(),
        required=False,
        allow_null=True,
        default=None,
    )
    # Required when assigning the Mentor role — determines the mentor tier.
    mentor_tier = serializers.ChoiceField(
        choices=UserMentor.MentorTier.choices,
        required=False,
        allow_null=True,
        default=None,
    )
    # Required for IG_MENTOR tier — list of Interest Group UUIDs.
    ig_ids = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        default=list,
    )
    # Required for CAMPUS_MENTOR / COMPANY_MENTOR tiers.
    org_id = serializers.CharField(required=False, allow_null=True, default=None)

    class Meta:
        model = UserRoleLink
        fields = ["user_id", "role_id", "guild", "mentor_tier", "ig_ids", "org_id"]

    def validate(self, data):
        from db.task import InterestGroup
        from db.organization import Organization
        from utils.types import OrganizationType

        guild       = data.get("guild")
        mentor_tier = data.get("mentor_tier")
        ig_ids      = data.get("ig_ids") or []
        org_id      = data.get("org_id")
        role_id     = data.get("role", {}).get("id") if isinstance(data.get("role"), dict) else None

        # Look up the actual role object for title check
        role_obj      = Role.objects.filter(id=role_id).first() if role_id else None
        is_mentor_role = role_obj and role_obj.title == RoleType.MENTOR.value
        is_intern_role = role_obj and role_obj.title == RoleType.INTERN.value

        errors = {}

        # ── Mentor validation ───────────────────────────────────────────────
        if is_mentor_role:
            if not mentor_tier:
                errors["mentor_tier"] = "mentor_tier is required when assigning the Mentor role."
            else:
                if mentor_tier == UserMentor.MentorTier.IG_MENTOR:
                    if not ig_ids:
                        errors["ig_ids"] = "ig_ids is required for IG_MENTOR tier."
                    else:
                        invalid_igs = [
                            ig_id for ig_id in ig_ids
                            if not InterestGroup.objects.filter(id=ig_id).exists()
                        ]
                        if invalid_igs:
                            errors["ig_ids"] = f"Invalid IG IDs: {', '.join(invalid_igs)}"

                elif mentor_tier in (
                    UserMentor.MentorTier.CAMPUS_MENTOR,
                    UserMentor.MentorTier.COMPANY_MENTOR,
                ):
                    if not org_id:
                        errors["org_id"] = f"org_id is required for {mentor_tier}."
                    else:
                        expected_type = (
                            OrganizationType.COLLEGE.value
                            if mentor_tier == UserMentor.MentorTier.CAMPUS_MENTOR
                            else OrganizationType.COMPANY.value
                        )
                        org = Organization.objects.filter(
                            id=org_id, org_type=expected_type
                        ).first()
                        if org is None:
                            errors["org_id"] = (
                                f"org_id must reference a valid {expected_type} organisation."
                            )
                        else:
                            data["_org"] = org

        # ── Intern validation ───────────────────────────────────────────────
        if is_intern_role and not guild:
            errors["guild"] = "guild is required when assigning the Intern role."

        if errors:
            raise serializers.ValidationError(errors)

        data['_is_mentor_role'] = is_mentor_role
        data['_is_intern_role'] = is_intern_role
        return data

    def create(self, validated_data):
        guild       = validated_data.pop("guild", None)
        mentor_tier = validated_data.pop("mentor_tier", None)
        ig_ids      = validated_data.pop("ig_ids", []) or []
        org         = validated_data.pop("_org", None)
        is_mentor_role = validated_data.pop("_is_mentor_role", False)
        is_intern_role = validated_data.pop("_is_intern_role", False)
        admin_user_id  = JWTUtils.fetch_user_id(self.context.get("request"))

        target_user_id = validated_data["user"]["id"]
        role_id        = validated_data["role"]["id"]
        now            = DateTimeUtils.get_current_utc_time()

        with transaction.atomic():
            # Duplicate check (Mentor role is per-user, not per-IG, going forward)
            existing = UserRoleLink.objects.filter(
                role_id=role_id,
                user_id=target_user_id,
            ).first()

            if not existing:
                validated_data["user_id"]      = (validated_data.pop("user"))["id"]
                validated_data["role_id"]      = (validated_data.pop("role"))["id"]
                validated_data["verified"]     = True
                validated_data["is_active"]    = True
                validated_data["created_by_id"] = admin_user_id
                validated_data["created_at"]   = now
                role_link = super().create(validated_data)
            else:
                role_link = existing

            # --- Mentor-specific provisioning ---
            # When the Mentor role is assigned, auto-create/approve UserMentor
            # plus all tier-specific linked rows (UserIgLink / UserOrganizationLink).
            if is_mentor_role and mentor_tier:
                from db.task import UserIgLink, InterestGroup

                # 1. Create / approve UserMentor record
                mentor_record, created = UserMentor.objects.get_or_create(
                    user_id=target_user_id,
                    mentor_tier=mentor_tier,
                    org=org,
                    defaults={
                        "status":           UserMentor.Status.APPROVED,
                        "preferred_ig_ids": ig_ids if ig_ids else None,
                        "verified_by_id":   admin_user_id,
                        "verified_at":      now,
                        "updated_by_id":    admin_user_id,
                        "updated_at":       now,
                        "created_by_id":    admin_user_id,
                        "created_at":       now,
                    },
                )
                if not created and mentor_record.status != UserMentor.Status.APPROVED:
                    mentor_record.status         = UserMentor.Status.APPROVED
                    mentor_record.verified_by_id = admin_user_id
                    mentor_record.verified_at    = now
                    mentor_record.updated_by_id  = admin_user_id
                    mentor_record.updated_at     = now
                    mentor_record.save(update_fields=[
                        "status", "verified_by_id", "verified_at",
                        "updated_by_id", "updated_at",
                    ])

                # 2. IG_MENTOR: create/activate UserIgLink per ig_id
                if mentor_tier == UserMentor.MentorTier.IG_MENTOR and ig_ids:
                    for ig_id in ig_ids:
                        ig = InterestGroup.objects.filter(id=ig_id).first()
                        if ig:
                            ig_link, _ = UserIgLink.objects.get_or_create(
                                user_id=target_user_id,
                                ig=ig,
                                defaults={
                                    "assignment_type": UserIgLink.AssignmentType.MENTOR,
                                    "is_active":       True,
                                    "assigned_by_id":  admin_user_id,
                                    "created_by_id":   admin_user_id,
                                    "created_at":      now,
                                },
                            )
                            if not ig_link.is_active:
                                ig_link.assignment_type = UserIgLink.AssignmentType.MENTOR
                                ig_link.is_active       = True
                                ig_link.assigned_by_id  = admin_user_id
                                ig_link.save(update_fields=[
                                    "assignment_type", "is_active", "assigned_by_id"
                                ])

                # 3. CAMPUS/COMPANY_MENTOR: create/verify UserOrganizationLink
                elif mentor_tier in (
                    UserMentor.MentorTier.CAMPUS_MENTOR,
                    UserMentor.MentorTier.COMPANY_MENTOR,
                ) and org:
                    from db.organization import UserOrganizationLink
                    org_link, _ = UserOrganizationLink.objects.get_or_create(
                        user_id=target_user_id,
                        org=org,
                        defaults={
                            "verified":      True,
                            "created_by_id": admin_user_id,
                            "created_at":    now,
                        },
                    )
                    if not org_link.verified:
                        org_link.verified = True
                        org_link.save(update_fields=["verified"])

                role_link._mentor_profile_created = created
            else:
                role_link._mentor_profile_created = False

            # --- Intern-specific provisioning ---
            # When the Intern role is assigned, automatically create (or reactivate)
            # the UserInternGuildLink row so the intern dashboard is immediately accessible.
            if is_intern_role and guild:
                from db.intern import UserInternGuildLink
                from utils.types import InternGuildStatus
                now = DateTimeUtils.get_current_utc_time()

                intern_link = UserInternGuildLink.objects.filter(
                    user_id=target_user_id
                ).first()

                if intern_link is None:
                    # Fresh onboarding
                    UserInternGuildLink.objects.create(
                        user_id=target_user_id,
                        guild=guild,
                        status=InternGuildStatus.ACTIVE.value,
                        created_by_id=admin_user_id,
                        updated_by_id=admin_user_id,
                    )
                    role_link._intern_guild_created = True
                else:
                    # Reactivate a previously inactive intern or update guild
                    changed = False
                    if intern_link.status == InternGuildStatus.INACTIVE.value:
                        intern_link.status = InternGuildStatus.ACTIVE.value
                        changed = True
                    if intern_link.guild != guild:
                        intern_link.guild = guild
                        changed = True
                    if changed:
                        intern_link.updated_by_id = admin_user_id
                        intern_link.save(update_fields=["status", "guild", "updated_by_id"])
                    role_link._intern_guild_created = False
            else:
                role_link._intern_guild_created = False

        return role_link


class UserRoleBulkAssignSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(required=True)
    role_id = serializers.CharField(required=True)
    created_by_id = serializers.CharField(required=True, allow_null=False)

    class Meta:
        model = UserRoleLink
        fields = [
            "id",
            "user_id",
            "role_id",
            "verified",
            "created_by_id",
            "created_at",
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation["user_id"] = instance.user.full_name if instance.user else None
        representation["role_id"] = instance.role.title if instance.role else None
        return representation
