from rest_framework import serializers
from db.user import User


class UserDashboardSerializer(serializers.ModelSerializer):
    total_karma = serializers.SerializerMethodField()

    def get_total_karma(self, obj):
        karma = 0
        if hasattr(obj, "total_karma_user"):
            karma = obj.total_karma_user.karma
        return karma

    class Meta:
        model = User

        fields = [
            "id",
            "discord_id",
            "mu_id",
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
            "total_karma"
        ]
