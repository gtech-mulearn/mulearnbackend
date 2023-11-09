import uuid
from rest_framework import serializers

from db.task import TaskList, KarmaActivityLog, TaskType
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils


class TaskListSerializer(serializers.ModelSerializer):
    channel = serializers.CharField(source="channel.name", required=False, default=None)
    type = serializers.CharField(source="type.title")
    level = serializers.CharField(source="level.name", required=False, default=None)
    ig = serializers.CharField(source="ig.name", required=False, default=None)
    org = serializers.CharField(source="org.title", required=False, default=None)
    total_karma_gainers = serializers.SerializerMethodField()

    created_by = serializers.CharField(source="created_by.fullname")
    updated_by = serializers.CharField(source="updated_by.fullname")

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
            "updated_at",
            "updated_by",
            "created_by",
            "created_at",
        ]

    def get_total_karma_gainers(self, obj):

        return obj.karma_activity_log_task.filter(
            appraiser_approved=True
        ).count()


class TaskModifySerializer(serializers.ModelSerializer):
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
        )


class TaskImportSerializer(serializers.ModelSerializer):
    created_by_id = serializers.CharField(required=True, allow_null=False)
    updated_by_id = serializers.CharField(required=True, allow_null=False)
    channel_id = serializers.CharField(required=False, allow_null=True)
    type_id = serializers.CharField(required=False, allow_null=True)
    org_id = serializers.CharField(required=False, allow_null=True)
    level_id = serializers.CharField(required=False, allow_null=True)
    ig_id = serializers.CharField(required=False, allow_null=True)

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

class TasktypeSerializer(serializers.ModelSerializer):
    updated_by=serializers.CharField(source='updated_by.fullname')
    created_by=serializers.CharField(source='created_by.fullname')

    class Meta:
        model = TaskType
        fields = ["id", "title","updated_by","updated_at","created_by","created_at"]

class TaskTypeCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model=TaskType
        fields=["title"]

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
        instance.updated_at=DateTimeUtils.get_current_utc_time(),
        instance.save()
        return instance




