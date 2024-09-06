from rest_framework import serializers
from db.events import Event, EventKarmaRequest
from db.user import User
from db.task import InterestGroup, LearningCircle, Organization
from datetime import datetime


class EventCreateSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    description = serializers.CharField()
    assets = serializers.JSONField(required=False)
    location = serializers.CharField()
    task_id = serializers.CharField(required=True)
    org_id = serializers.CharField(required=False)
    lc_id = serializers.CharField(required=False)
    ig_id = serializers.CharField(required=False)

    def create(self, validated_data):
        user = User.objects.get(id=self.context.get("user_id"))
        validated_data["created_by"] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_at"] = datetime.now()
        return super().update(instance, validated_data)

    class Meta:
        model = Event
        fields = [
            "name",
            "description",
            "assets",
            "location",
            "task_id",
            "org_id",
            "lc_id",
            "ig_id",
        ]


class EventSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    name = serializers.CharField()
    description = serializers.CharField()
    assets = serializers.JSONField()
    location = serializers.CharField()
    task_id = serializers.CharField(source="task_id.title")
    suggestions = serializers.CharField()
    is_approved = serializers.BooleanField()
    approved_by = serializers.CharField(source="approved_by.full_name")
    created_by = serializers.CharField(source="created_by.full_name")
    org_id = serializers.CharField(source="org_id.name")
    lc_id = serializers.CharField(source="lc_id.name")
    ig_id = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_ig_id(self, obj):
        return InterestGroup.objects.filter(id__in=obj.ig_id).values("name")

    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "description",
            "assets",
            "location",
            "task_id",
            "suggestions",
            "is_approved",
            "approved_by",
            "created_by",
            "org_id",
            "lc_id",
            "ig_id",
            "created_at",
            "updated_at",
        ]
