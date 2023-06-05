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

    def create(self, validated_data):
        # user_id = JWTUtils.fetch_user_id(self.context["request"])
        user_id = "000b9f56-dda4-4f73-8be3-44e0574c1d08"
        user = User.objects.get(id=user_id)
        
        validated_data['created_by'] = user
        validated_data['created_at'] = DateTimeUtils.get_current_utc_time()
        validated_data['updated_by'] = user
        validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()
        
        return super().create(validated_data)
