import uuid

from rest_framework import serializers

from db.user import Role, User, UserRoleLink, UserMentor
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils, DiscordWebhooks
from utils.types import WebHookActions, WebHookCategory
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
    # Required when assigning a Mentor role — links the role to a specific IG.
    # Leave null/omit for platform-wide roles (e.g., Admin, Campus Lead).
    ig_id = serializers.CharField(required=False, allow_null=True, default=None)

    class Meta:
        model = UserRoleLink
        fields = ["user_id", "role_id", "ig_id"]

    def validate(self, data):
        from db.task import InterestGroup
        ig_id = data.get("ig_id")
        role_id = data.get("role", {}).get("id") if isinstance(data.get("role"), dict) else None

        # Look up the actual role object for title check
        role_obj = Role.objects.filter(id=role_id).first() if role_id else None
        is_mentor_role = role_obj and role_obj.title == 'Mentor'

        # Mentor role MUST have an IG — platform-wide mentor makes no sense
        if is_mentor_role and not ig_id:
            raise serializers.ValidationError(
                {"ig_id": "ig_id is required when assigning a Mentor role."}
            )

        if ig_id and not InterestGroup.objects.filter(id=ig_id).exists():
            raise serializers.ValidationError({"ig_id": "Interest group not found."})

        data['_is_mentor_role'] = is_mentor_role
        return data

    def create(self, validated_data):
        ig_id = validated_data.pop("ig_id", None)
        is_mentor_role = validated_data.pop("_is_mentor_role", False)
        admin_user_id = JWTUtils.fetch_user_id(self.context.get("request"))

        target_user_id = validated_data["user"]["id"]
        role_id = validated_data["role"]["id"]

        with transaction.atomic():
            # Duplicate check — same user can be Mentor in multiple IGs
            existing = UserRoleLink.objects.filter(
                role_id=role_id,
                user_id=target_user_id,
                ig_id=ig_id,
            ).first()

            if not existing:
                validated_data["user_id"] = (validated_data.pop("user"))["id"]
                validated_data["role_id"] = (validated_data.pop("role"))["id"]
                validated_data["ig_id"] = ig_id
                validated_data["verified"] = True
                validated_data["is_active"] = True
                validated_data["created_by_id"] = admin_user_id
                validated_data["created_at"] = DateTimeUtils.get_current_utc_time()
                role_link = super().create(validated_data)
            else:
                role_link = existing

            # --- Mentor-specific provisioning ---
            # When a Mentor role is assigned to an IG, automatically create the
            # UserMentor profile row so the user can immediately switch persona.
            if is_mentor_role and ig_id:
                target_user = User.objects.filter(id=target_user_id).first()
                admin_user = User.objects.filter(id=admin_user_id).first()
                _, created = UserMentor.objects.get_or_create(
                    user_id=target_user_id,
                    defaults={
                        'mentor_tier': UserMentor.MentorTier.NORMAL,
                        'is_verified': False,
                        'created_by': admin_user,
                        'updated_by': admin_user,
                    }
                )
                # Attach the flag so the view can include it in the response
                role_link._mentor_profile_created = created
            else:
                role_link._mentor_profile_created = False

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
