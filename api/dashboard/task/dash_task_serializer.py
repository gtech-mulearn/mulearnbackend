import uuid

from rest_framework import serializers

from db.task import KarmaActivityLog, TaskList, TaskType
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils


class TaskListPublicSerializer(serializers.ModelSerializer):
    channel = serializers.CharField(source="channel.name", required=False, default=None)
    discord_id = serializers.CharField(source="channel.discord_id", required=False, default=None)
    type = serializers.CharField(source="type.title")
    level = serializers.CharField(source="level.name", required=False, default=None)
    ig = serializers.CharField(source="ig.name", required=False, default=None)
    event_id = serializers.CharField(source="event_fk_id", required=False, allow_null=True)
    company_name = serializers.CharField(
        source="requested_by.company_profile.name", required=False, default=None
    )
    completed = serializers.SerializerMethodField()

    class Meta:
        model = TaskList
        fields = [
            "id",
            "hashtag",
            "title",
            "description",
            "karma",
            "channel",
            "discord_id",
            "type",
            "variable_karma",
            "level",
            "ig",
            "event",
            "event_id",
            "company_name",
            "completed",
        ]

    def get_completed(self, obj):
        completed_task_ids = self.context.get("completed_task_ids")
        if completed_task_ids is None:
            return False
        return obj.id in completed_task_ids


class TaskListSerializer(serializers.ModelSerializer):
    channel = serializers.CharField(source="channel.name", required=False, default=None)
    type = serializers.CharField(source="type.title")
    level = serializers.CharField(source="level.name", required=False, default=None)
    ig = serializers.CharField(source="ig.name", required=False, default=None)
    org = serializers.CharField(source="org.title", required=False, default=None)
    event_id = serializers.CharField(source="event_fk_id", required=False, allow_null=True)
    total_karma_gainers = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()

    created_by = serializers.CharField(source="created_by.full_name")
    updated_by = serializers.CharField(source="updated_by.full_name")

    class Meta:
        model = TaskList
        fields = [
            "id",
            "hashtag",
            "title",
            "description",
            "karma",
            "total_karma_gainers",
            "channel",
            "type",
            "active",
            "variable_karma",
            "usage_count",
            "level",
            "org",
            "ig",
            "event",
            "event_id",
            "updated_at",
            "updated_by",
            "created_by",
            "created_at",
            "bonus_time",
            "bonus_karma",
            "skills",
        ]

    def get_total_karma_gainers(self, obj):
        if hasattr(obj, 'total_karma_gainers_count'):
            return obj.total_karma_gainers_count
        return obj.karma_activity_log_task.filter(appraiser_approved=True).count()

    def get_skills(self, obj):
        """Get all skills linked to this task"""
        return [
            {'id': link.skill.id, 'name': link.skill.name, 'code': link.skill.code}
            for link in obj.skill_links.all()
        ]


class TaskModifySerializer(serializers.ModelSerializer):
    event_id = serializers.CharField(source="event_fk_id", required=False, allow_null=True)

    class Meta:
        model = TaskList
        fields = (
            "hashtag",
            "discord_link",
            "title",
            "description",
            "karma",
            "channel",
            "type",
            "active",
            "variable_karma",
            "usage_count",
            "level",
            "org",
            "ig",
            "event",
            "updated_by",
            "created_by",
            "bonus_karma",
            "bonus_time",
            "event_id",
        )

    def validate_event_id(self, value):
        if not value:
            return value

        try:
            uuid.UUID(str(value))
        except (ValueError, TypeError):
            raise serializers.ValidationError("Invalid event id.")

        return value


class TaskImportSerializer(serializers.ModelSerializer):
    created_by_id = serializers.CharField(required=True, allow_null=False)
    updated_by_id = serializers.CharField(required=True, allow_null=False)
    channel_id = serializers.CharField(required=False, allow_null=True)
    type_id = serializers.CharField(required=False, allow_null=True)
    org_id = serializers.CharField(required=False, allow_null=True)
    level_id = serializers.CharField(required=False, allow_null=True)
    ig_id = serializers.CharField(required=False, allow_null=True)
    usage_count = serializers.IntegerField(allow_null=True)
    variable_karma = serializers.BooleanField(allow_null=True)

    class Meta:
        model = TaskList
        fields = [
            "id",
            "hashtag",
            "discord_link",
            "title",
            "description",
            "karma",
            "channel_id",
            "type_id",
            "org_id",
            "event",
            "level_id",
            "ig_id",
            "active",
            "variable_karma",
            "usage_count",
            "created_by_id",
            "updated_by_id",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation["channel_id"] = (
            instance.channel.name if instance.channel else None
        )
        representation["type_id"] = instance.type.title if instance.type else None
        representation["org_id"] = instance.org.code if instance.org else None
        representation["level_id"] = instance.level.name if instance.level else None
        representation["ig_id"] = instance.ig.name if instance.ig else None

        return representation

    def validate_usage_count(self, value):
        if value is None:
            return 1
        return value

    def validate_variable_karma(self, value):
        if value is None:
            return False
        return value


class TasktypeSerializer(serializers.ModelSerializer):
    updated_by = serializers.CharField(source="updated_by.full_name")
    created_by = serializers.CharField(source="created_by.full_name")

    class Meta:
        model = TaskType
        fields = ["id", "title", "updated_by", "updated_at", "created_by", "created_at"]


class TaskTypeCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskType
        fields = ["title"]

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        return TaskType.objects.create(
            id=uuid.uuid4(),
            title=validated_data.get("title"),
            updated_by_id=user_id,
            updated_at=DateTimeUtils.get_current_utc_time(),
            created_by_id=user_id,
            created_at=DateTimeUtils.get_current_utc_time(),
        )

    def update(self, instance, validated_data):
        updated_title = validated_data.get("title")
        instance.title = updated_title
        user_id = JWTUtils.fetch_user_id(self.context.get("request"))
        instance.updated_by_id = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance
