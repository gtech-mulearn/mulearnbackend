import uuid
from utils.utils import DateTimeUtils
from rest_framework import serializers
from db.organization import College, Organization, OrgDiscordLink


class CollegeListSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.fullname")
    updated_by = serializers.CharField(source="updated_by.fullname")
    org = serializers.CharField(source="org.title")
    discord_link = serializers.SerializerMethodField()

    class Meta:
        model = College
        fields = "__all__"

    def get_discord_link(self, obj):
        return obj.org.org_discord_link_org_id.exists()


class CollegeCreateDeleteSerializer(serializers.ModelSerializer):
    org_id = serializers.CharField(
        required=True, error_messages={"required": "note field must not be left blank."}
    )

    level = serializers.CharField(
        required=True, error_messages={"required": "note field must not be left blank."}
    )

    class Meta:
        model = College
        fields = ["level", "org_id"]

    def validate(self, data):
        if not Organization.objects.filter(id=data.get("org_id")).exists():
            raise serializers.ValidationError("Invalid college")

        if College.objects.filter(org_id=data.get("org_id")).exists():
            raise serializers.ValidationError("College already exists")

        return data

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        return College.objects.create(
            id=uuid.uuid4(),
            org_id=validated_data.get("org_id"),
            level=validated_data.get("level"),
            updated_by_id=user_id,
            updated_at=DateTimeUtils.get_current_utc_time(),
            created_by_id=user_id,
            created_at=DateTimeUtils.get_current_utc_time(),
        )

    def destroy(self, obj):
        obj.delete()


class CollegeEditSerializer(serializers.ModelSerializer):
    level = serializers.CharField(
        required=True, error_messages={"required": "note field must not be left blank."}
    )

    class Meta:
        model = College
        fields = ["level"]

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        instance.level = validated_data.get("level")
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.updated_by_id = user_id
        instance.save()
        return instance
