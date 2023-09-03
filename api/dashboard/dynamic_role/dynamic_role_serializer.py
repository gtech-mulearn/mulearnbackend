import uuid

from rest_framework import serializers

from db.user import Role, DynamicRole
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils

class DynamicRoleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DynamicRole
        fields = ["type", "role"]

    def create(self, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))

        validated_data['id'] = uuid.uuid4()
        validated_data['updated_by_id'] = user_id
        validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()
        validated_data['created_by_id'] = user_id
        validated_data['created_at'] = DateTimeUtils.get_current_utc_time()

        return DynamicRole.objects.create(**validated_data)
    
class DynamicRoleListSerializer(serializers.ModelSerializer):
    role = serializers.CharField()

    class Meta:
        model = DynamicRole
        fields = ["type", "role"]