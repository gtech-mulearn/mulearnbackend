from rest_framework import serializers

from db.task import TaskList


class TaskListSerializer(serializers.ModelSerializer):
    channel = serializers.CharField(source="channel.name", required=False, default=None)
    type = serializers.CharField(source="type.title")
    level = serializers.CharField(source="level.name", required=False, default=None)
    ig = serializers.CharField(source="ig.name", required=False, default=None)
    org = serializers.CharField(source="org.title", required=False, default=None)
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
