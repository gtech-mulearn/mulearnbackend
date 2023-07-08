import uuid

from rest_framework import serializers

from db.task import TaskList, Channel, InterestGroup, Organization, Level
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils


class TaskListSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='created_by.fullname')
    updated_by = serializers.CharField(source='updated_by.fullname')
    channel = serializers.CharField(source='channel.name')
    type = serializers.CharField(source='type.title')
    level = serializers.CharField(source='level.name', allow_null=True)

    # ig = serializers.CharField(source='ig.name')

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
            "ig",
            "updated_at",
            "updated_by",
            "created_by",
            "created_at"
        ]


class TaskCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = TaskList
        fields = ("hashtag", "title", "description", "karma", "channel", "type", "org",
                  "level", "ig", "active", "variable_karma", "usage_count", )

    def create(self, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))

        validated_data['id'] = uuid.uuid4()
        validated_data['updated_by_id'] = user_id
        validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()
        validated_data['created_by_id'] = user_id
        validated_data['created_at'] = DateTimeUtils.get_current_utc_time()

        return TaskList.objects.create(**validated_data)


class TaskUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = TaskList
        fields = ("hashtag", "title", "karma", "active", "variable_karma", "usage_count", )

    def update(self, instance, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))

        instance.hashtag = validated_data.get('hashtag', instance.hashtag)
        instance.title = validated_data.get('title', instance.title)
        instance.karma = validated_data.get('karma', instance.karma)
        instance.active = validated_data.get('active', instance.active)
        instance.variable_karma = validated_data.get('variable_karma', instance.variable_karma)
        instance.usage_count = validated_data.get('usage_count', instance.usage_count)
        instance.updated_by_id = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()

        return instance


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