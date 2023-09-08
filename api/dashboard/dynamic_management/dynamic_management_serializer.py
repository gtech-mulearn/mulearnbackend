import uuid

from rest_framework import serializers
from django.db.models import Q
from db.user import Role, DynamicRole, DynamicUser, User
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

class DynamicUserCreateSerializer(serializers.ModelSerializer):
    type = serializers.CharField(required=True, error_messages={
        'required': 'type field must not be left blank.'
        })
    user = serializers.CharField(required=True, error_messages={
        'required': 'user field must not be left blank.'
        })
    
    class Meta:
        model = DynamicUser
        fields = ["type", "user"]

    def create(self, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))

        validated_data['id'] = uuid.uuid4()
        validated_data['updated_by_id'] = user_id
        validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()
        validated_data['created_by_id'] = user_id
        validated_data['created_at'] = DateTimeUtils.get_current_utc_time()

        return DynamicUser.objects.create(**validated_data)
    
    def validate(self, data):
        if DynamicUser.objects.filter(type=data['type'], user=data['user']).first():
            raise serializers.ValidationError("Dynamic User already exists")
        return data
    
    def validate_user(self, value):
        user = User.objects.filter(Q(mu_id=value) | Q(email=value)).first()
        if user is None:
            raise serializers.ValidationError("Enter a valid user email")
        return user
    
class DynamicUserListSerializer(serializers.ModelSerializer):
    users = serializers.SerializerMethodField()

    def get_users(self, obj):
        dynamic_users = DynamicUser.objects.filter(type=obj['type'])
        user_data = [{'name': f"{user.user.first_name} {user.user.last_name if user.user.last_name else ''}",
                    'muid': user.user.mu_id,  # Replace 'muid' with the actual field name in your model
                    'email': user.user.email} for user in dynamic_users]
        return user_data

    class Meta:
        model = DynamicUser
        fields = ["type", "users"]

class DynamicUserUpdateSerializer(serializers.ModelSerializer):
    new_user = serializers.CharField(required=True, error_messages={
        'required': 'new_user field must not be left blank.'
    })

    class Meta:
        model = DynamicUser
        fields = ["new_user"]

    def update(self, instance, validated_data):
        instance.updated_by_id = self.context.get('user_id')
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        new_user = validated_data.get('new_user')
        if DynamicUser.objects.filter(type=instance.type, user=new_user).first():
            raise serializers.ValidationError("Dynamic User already exists")
        instance.user = new_user if new_user else instance.user
        instance.save()
        return instance 

    def validate_new_user(self, value):
        new_user = User.objects.filter(Q(mu_id=value) | Q(email=value)).first()
        if new_user is None:
            raise serializers.ValidationError("Enter a valid user email")
        return new_user

    def destroy(self, obj):
        obj.delete()

class RoleDropDownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["title"]