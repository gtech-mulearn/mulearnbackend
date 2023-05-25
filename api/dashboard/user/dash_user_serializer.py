from rest_framework import serializers
from db.user import User, UserRoleLink, Role


class UserDashboardSerializer(serializers.ModelSerializer):
    total_karma = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    def get_total_karma(self, obj):
        karma = obj.total_karma_user.karma if hasattr(
            obj, "total_karma_user") else 0
        return karma

    def get_roles(self, user):
        if role_ids := UserRoleLink.objects.filter(user=user).values_list(
            'role_id', flat=True
        ):
            roles = Role.objects.filter(id__in=role_ids)
            return [role.title for role in roles]
        else:
            return []

    class Meta:
        model = User
        exclude = ("password",)
        extra_fields = ["total_karma", "roles"]
        read_only_fields = ["id", "created_at", "total_karma"]


class UserSerializer(serializers.ModelSerializer):
    muid = serializers.CharField(source="mu_id")
    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")
    existInGuild = serializers.CharField(source="exist_in_guild")
    joined = serializers.CharField(source="created_at")
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["muid", "firstName", "lastName", "fullname", "fullname", "email", "mobile", "gender", "dob",
                  "active",
                  "existInGuild", "joined", "roles"]

    def get_roles(self, obj):
        roles = []

        for user_role_link in obj.user_role_link_user.all():
            roles.append(user_role_link.role.title)

        return roles
