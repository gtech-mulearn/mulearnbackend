import uuid

from rest_framework import serializers

from db.user import Role, DynamicRole
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils

class DynamicRoleCreateSerializer(serializers.ModelSerializer):
    type = serializers.CharField(required=True, error_messages={
        'required': 'type field must not be left blank.'
        })
    role = serializers.CharField(required=True, error_messages={
        'required': 'role field must not be left blank.'
        })

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

class DynamicRoleUpdateSerializer(serializers.ModelSerializer):
    new_role = serializers.CharField(required=True, error_messages={
        'required': 'new_role field must not be left blank.'
    })

    class Meta:
        model = DynamicRole
        fields = ["new_role"]

    def update(self, instance, validated_data):
        instance.updated_by_id = self.context.get('user_id')
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        new_role = validated_data.get('new_role')
        if DynamicRole.objects.filter(type=instance.type, role=new_role).first():
            raise serializers.ValidationError("Dynamic Role already exists")
        instance.role = new_role if new_role else instance.role
        instance.save()
        return instance 

    def validate_new_role(self, value):
        new_role = Role.objects.filter(title=value).first()
        if new_role is None:
            raise serializers.ValidationError("Enter a valid role name")
        return new_role

    def destroy(self, obj):
        obj.delete()