import uuid

from rest_framework import serializers

from db.user import Role, DynamicRole
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils

class DynamicRoleCreateSerializer(serializers.ModelSerializer):
    role = serializers.CharField(required=True)

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
    
    def validate(self, data):
        if DynamicRole.objects.filter(type=data['type'], role=data['role']).first():
            raise serializers.ValidationError("Dynamic Role already exists")
        return data
    
    def validate_role(self, value):
        role = Role.objects.filter(title=value).first()
        if role is None:
            raise serializers.ValidationError("Enter a valid role name")
        return role
    
class DynamicRoleListSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    def get_roles(self, obj):
        dynamic_roles = DynamicRole.objects.filter(type=obj['type']).values_list('role__title', flat=True)
        return list(dynamic_roles)

    class Meta:
        model = DynamicRole
        fields = ["type", "roles"]