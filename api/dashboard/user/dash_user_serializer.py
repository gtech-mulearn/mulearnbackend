from rest_framework import serializers
from db.user import User


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


# class UserVerificationSerializer(serializers.ModelSerializer):
#     role_id = serializers.SerializerMethodField()
#     role_title = serializers.SerializerMethodField()

#     def get_role_id(self, user):
#         role_ids_and_titles = UserRoleLink.objects.filter(user=user, verified=False).values_list('role_id', 'role__title')
#         return [role_id for role_id, _ in role_ids_and_titles]

#     def get_role_title(self, user):
#         role_ids_and_titles = UserRoleLink.objects.filter(user=user, verified=False).values_list('role_id', 'role__title')
#         return [role_title for _, role_title in role_ids_and_titles]

#     class Meta:
#         model = User
#         fields = ["user_id", "discord_id", "mu_id", "first_name", "last_name", "active", "exist_in_guild", "verified", "role_id", "role_title"]

