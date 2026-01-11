from rest_framework import serializers

from db.task import TaskReport
from utils.utils import DateTimeUtils
from utils.types import ManagementType

class TaskReportSerializer(serializers.ModelSerializer):
    reporter = serializers.CharField(source="reporter.fullname")
    offender = serializers.CharField(source="offender.fullname")
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = TaskReport
        fields = [
            "id",
            "reporter",
            "offender",
            "message_id",
            "reason",
            "proof_link",
            "status",
            "created_at",
            "updated_at",
        ]

    def get_created_at(self, obj):
        return DateTimeUtils.format_datetime(obj.created_at)

    def get_updated_at(self, obj):
        return DateTimeUtils.format_datetime(obj.updated_at)


class TaskReportUpdateSerializer(serializers.ModelSerializer):
    updated_by = serializers.CharField(required=False)

    class Meta:
        model = TaskReport
        fields = ["status", "updated_by"]

    def update(self, instance, validated_data):
        instance.status = validated_data.get("status", instance.status)
        instance.updated_by_id = self.context.get("user_id")
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance
