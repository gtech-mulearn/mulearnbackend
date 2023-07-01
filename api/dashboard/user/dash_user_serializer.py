from rest_framework import serializers

from db.organization import Organization, UserOrganizationLink
from db.user import User, UserRoleLink
from utils.types import OrganizationType


class UserDashboardSerializer(serializers.ModelSerializer):
    total_karma = serializers.IntegerField()
    company = serializers.CharField()
    college = serializers.CharField()
    department = serializers.CharField()
    graduation_year = serializers.CharField()

    class Meta:
        model = User
        fields = [
            "id",
            "discord_id",
            "first_name",
            "last_name",
            "email",
            "mobile",
            "gender",
            "dob",
            "admin",
            "active",
            "exist_in_guild",
            "created_at",
            "company",
            "college",
            "total_karma",
            "department",
            "graduation_year",
        ]
        read_only_fields = ["id", "created_at", "total_karma"]


class UserSerializer(serializers.ModelSerializer):
    muid = serializers.CharField(source="mu_id")
    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")
    existInGuild = serializers.BooleanField(source="exist_in_guild")
    joined = serializers.CharField(source="created_at")
    roles = serializers.SerializerMethodField()
    profilePic = serializers.CharField(source="profile_pic")

    class Meta:
        model = User
        fields = [
            "muid",
            "firstName",
            "lastName",
            "email",
            "mobile",
            "gender",
            "dob",
            "active",
            "existInGuild",
            "joined",
            "roles",
            "profilePic"
        ]

    def get_roles(self, obj):
        return [
            user_role_link.role.title
            for user_role_link in obj.user_role_link_user.all()
        ]


class UserVerificationSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField(source="user.fullname")
    user_id = serializers.ReadOnlyField(source="user.id")
    discord_id = serializers.ReadOnlyField(source="user.discord_id")
    mu_id = serializers.ReadOnlyField(source="user.mu_id")
    role_title = serializers.ReadOnlyField(source="role.title")

    class Meta:
        model = UserRoleLink
        fields = [
            "id",
            "user_id",
            "discord_id",
            "mu_id",
            "full_name",
            "verified",
            "role_id",
            "role_title",
        ]
