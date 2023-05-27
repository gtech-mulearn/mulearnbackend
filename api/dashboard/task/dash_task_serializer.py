from rest_framework import serializers
from db.task import TaskList

class TaskListSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='created_by.fullname')
    updated_by = serializers.CharField(source='updated_by.fullname')
    channel = serializers.CharField(source='channel.name')
    type = serializers.CharField(source='type.title')
    level = serializers.CharField(source='level.name')
    ig = serializers.CharField(source='ig.name')


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
