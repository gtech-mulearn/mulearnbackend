from rest_framework import serializers
from db.user import User

class UserDashboardSerializer(serializers.ModelSerializer):
    total_karma = serializers.SerializerMethodField()

    def get_total_karma(self, obj):
        karma = obj.total_karma_user.karma if hasattr(obj, "total_karma_user") else 0
        return karma

    class Meta:
        model = User
        exclude = ('password',)
        extra_fields = ['total_karma']
        read_only_fields = ["id", "created_at", 'total_karma']