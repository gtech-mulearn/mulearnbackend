from rest_framework import serializers

from db.user import User, UserRoleLink


class UserDashboardSerializer(serializers.ModelSerializer):
    total_karma = serializers.SerializerMethodField()

    def get_total_karma(self, obj):
        karma = obj.total_karma_user.karma if hasattr(obj, "total_karma_user") else 0
        return karma

    class Meta:
        model = User
        exclude = ("password",)
        extra_fields = ["total_karma"]
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
