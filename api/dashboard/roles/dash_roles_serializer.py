from rest_framework import serializers
from db.user import Role, User
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils

class RoleDashboardSerializer(serializers.ModelSerializer):

    class Meta:
        model = Role
        fields = "__all__"
        read_only_fields = ["id", "created_at","created_by"]
        
    def update(self, instance, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context["request"])
        user = User.objects.get(id=user_id)
        # Set 'updated_by' with authenticated user
        validated_data["updated_by"] = user
        # Set 'updated_at' with current timestamp
        validated_data["updated_at"] = DateTimeUtils.get_current_utc_time()

        return super().update(instance, validated_data)