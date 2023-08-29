import uuid

from rest_framework import serializers

from db.user import Role, User, UserRoleLink
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils


class RoleDashboardSerializer(serializers.ModelSerializer):
    updated_by = serializers.CharField(source="updated_by.fullname")
    created_by = serializers.CharField(source="created_by.fullname")
    users_with_role = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_at",
            "created_by",
            "updated_by",
            "updated_at",
            "users_with_role",
        ]

    def update(self, instance, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context["request"])
        user = User.objects.get(id=user_id)

        validated_data["updated_by"] = user
        validated_data["updated_at"] = DateTimeUtils.get_current_utc_time()

        return super().update(instance, validated_data)

    def create(self, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context["request"])
        user = User.objects.get(id=user_id)

        validated_data["id"] = uuid.uuid4()
        validated_data["created_by"] = validated_data["updated_by"] = user
        validated_data["created_at"] = validated_data[
            "updated_at"
        ] = DateTimeUtils.get_current_utc_time()

        return super().create(validated_data)

    def get_users_with_role(self, obj):
        return len(UserRoleLink.objects.filter(role_id=obj.id, verified=True))


class UserRoleSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "fullname", "mu_id"]


class UserRoleCreateSerializer(serializers.ModelSerializer):
    
    user_id = serializers.CharField(required=True, source="user.id")
    role_id = serializers.CharField(required=True, source="role.id")
    class Meta:
        model = UserRoleLink
        fields = ["user_id", "role_id"]

    def create(self, validated_data):
        if user_role_link := UserRoleLink.objects.filter(
            role_id=validated_data["role"]["id"], user_id=validated_data["user"]["id"]
        ).first():
            return user_role_link

        user_id = JWTUtils.fetch_user_id(self.context.get("request"))
        
        validated_data["user_id"] = (validated_data.pop("user"))["id"]
        validated_data["role_id"] = (validated_data.pop("role"))["id"]
        validated_data["verified"] = True
        validated_data["created_by_id"] = user_id
        validated_data["created_at"] = DateTimeUtils.get_current_utc_time()
        
        return super().create(validated_data)
