from rest_framework import serializers
from db.task import TaskList


class TaskListSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='created_by.fullname')
    updated_by = serializers.CharField(source='created_by.fullname')

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
