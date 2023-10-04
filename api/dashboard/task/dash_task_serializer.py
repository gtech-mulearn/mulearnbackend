import uuid

from rest_framework import serializers

from db.task import TaskList, Channel, InterestGroup, Organization, Level, TaskType
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils


class TaskListSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='created_by.fullname')
    updated_by = serializers.CharField(source='updated_by.fullname')
    channel = serializers.CharField(source='channel.name')
    type = serializers.CharField(source='type.title')
    level = serializers.CharField(source='level.name')
    ig = serializers.CharField(source='ig.name')
    org = serializers.CharField(source='org.title')

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
            "created_at"
        ]


class TaskCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskList
        fields = ("hashtag", "title", "description", "karma", "channel", "type", "org",
                  "level", "ig", "active", "variable_karma", "usage_count",)

    def create(self, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))

        validated_data['id'] = uuid.uuid4()
        validated_data['updated_by_id'] = user_id
        validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()
        validated_data['created_by_id'] = user_id
        validated_data['created_at'] = DateTimeUtils.get_current_utc_time()

        return TaskList.objects.create(**validated_data)


class TaskUpdateSerializer(serializers.ModelSerializer):
    channel = serializers.CharField(required=False)
    type = serializers.CharField(required=False)
    org = serializers.CharField(required=False)
    level = serializers.CharField(required=False)
    ig = serializers.CharField(required=False)
    variable_karma = serializers.BooleanField(required=False)

    class Meta:
        model = TaskList
        fields = ("hashtag", "title", "karma", "active", "variable_karma", "usage_count", "channel", "type", "org",
                  "level", "ig")

    def update(self, instance, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))
        instance.hashtag = validated_data.get('hashtag', instance.hashtag)
        instance.title = validated_data.get('title', instance.title)
        instance.karma = validated_data.get('karma', instance.karma)
        instance.active = validated_data.get('active', instance.active)
        instance.variable_karma = validated_data.get('variable_karma', instance.variable_karma)
        instance.usage_count = validated_data.get('usage_count', instance.usage_count)
        instance.channel = validated_data.get('channel', instance.channel)
        instance.type = validated_data.get('type', instance.type)
        instance.org = validated_data.get('org', instance.org)
        instance.level = validated_data.get('level', instance.level)
        instance.ig = validated_data.get('ig', instance.ig)
        instance.updated_by_id = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()

        return instance

    def validate_channel(self, value):
        channel = Channel.objects.filter(id=value).first()
        if channel is None:
            raise serializers.ValidationError("Enter a valid channel id")
        return channel

    def validate_type(self, value):
        task_type = TaskType.objects.filter(id=value).first()
        if task_type is None:
            raise serializers.ValidationError("Enter a valid task type id")
        return task_type

    def validate_org(self, value):
        org = Organization.objects.filter(id=value).first()
        if org is None:
            raise serializers.ValidationError("Enter a valid organization id")
        return org

    def validate_level(self, value):
        level = Level.objects.filter(id=value).first()
        if level is None:
            raise serializers.ValidationError("Enter a valid level id")
        return level

    def validate_ig(self, value):
        ig = InterestGroup.objects.filter(id=value).first()
        if ig is None:
            raise serializers.ValidationError("Enter a valid interest group id")
        return ig


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
        fields = ("id", "hashtag", "title", "description", "karma", "channel_id", "type_id", "org_id", "event",
                  "level_id", "ig_id", "active", "variable_karma", "usage_count", "created_by_id", "updated_by_id",
                  "created_at", "updated_at")


class ChannelDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = ("id", "name")


class IGDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterestGroup
        fields = ("id", "name")


class OrganizationDropdownSerialize(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ("id", "title")


class LevelDropdownSerialize(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ("id", "name")


class TaskTypeDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskType
        fields = ("id", "title")
