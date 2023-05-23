from rest_framework import serializers
from db.user import User, UserRoleLink, Role


class UserDashboardSerializer(serializers.ModelSerializer):
    total_karma = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    def get_total_karma(self, obj):
        karma = obj.total_karma_user.karma if hasattr(obj, "total_karma_user") else 0
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
