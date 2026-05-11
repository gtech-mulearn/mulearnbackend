from rest_framework import serializers

from db.task import KarmaActivityLog
from db.mentor_task_request import MentorTaskRequest


class TaskQueueSerializer(serializers.ModelSerializer):
    """
    Serializes a KarmaActivityLog entry for the mentor task review queue.
    """
    mentee_id = serializers.CharField(source="user.id")
    mentee_name = serializers.CharField(source="user.full_name")
    task_id = serializers.CharField(source="task.id")
    task_title = serializers.CharField(source="task.title")
    task_hashtag = serializers.CharField(source="task.hashtag")
    task_karma = serializers.IntegerField(source="task.karma")
    ig_name = serializers.SerializerMethodField()

    class Meta:
        model = KarmaActivityLog
        fields = [
            "id",
            "mentee_id",
            "mentee_name",
            "task_id",
            "task_title",
            "task_hashtag",
            "task_karma",
            "ig_name",
            "mentor_review_status",
            "mentor_review_feedback",
            "created_at",
        ]

    def get_ig_name(self, obj):
        if obj.task and obj.task.ig:
            return obj.task.ig.name
        return None


class MentorTaskRequestSerializer(serializers.ModelSerializer):
    """Serializes a MentorTaskRequest for list/detail responses."""
    mentor_name = serializers.CharField(source="mentor.full_name", read_only=True)
    ig_name     = serializers.CharField(source="ig.name",          read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    created_task_hashtag = serializers.SerializerMethodField()

    class Meta:
        model = MentorTaskRequest
        fields = [
            "id",
            "mentor_name",
            "ig_name",
            "title",
            "hashtag",
            "karma",
            "description",
            "status",
            "admin_note",
            "reviewed_by_name",
            "reviewed_at",
            "created_task_hashtag",
            "created_at",
        ]

    def get_reviewed_by_name(self, obj):
        return obj.reviewed_by.full_name if obj.reviewed_by else None

    def get_created_task_hashtag(self, obj):
        return obj.created_task.hashtag if obj.created_task else None
