from rest_framework import serializers
from django.utils.timezone import now
from datetime import timedelta

from db.intern import InternDailyTimesheet, InternTask
from utils.types import InternSubmissionStatus

class InternTimesheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternDailyTimesheet
        fields = [
            'entry_date', 'task', 'category', 'description',
            'hours', 'blockers', 'task_status', 'remark',
            'end_of_day_note', 'edit_reason'
        ]

    def validate(self, data):
        entry_date = data.get('entry_date')
        today = now().date()
        yesterday = today - timedelta(days=1)

        if entry_date > today:
            raise serializers.ValidationError({"entry_date": "Future dates are not allowed."})
        
        if entry_date < yesterday and not data.get('edit_reason'):
            raise serializers.ValidationError({"edit_reason": "Reason is required for late submissions."})

        task = data.get('task')
        task_status = data.get('task_status')
        if task and not task_status:
            raise serializers.ValidationError({"task_status": "Task status is required when a task is selected."})
        if not task and task_status:
            raise serializers.ValidationError({"task_status": "Cannot provide task status without a task."})

        if data.get('hours', 0) <= 0:
            raise serializers.ValidationError({"hours": "Hours must be greater than 0."})

        return data

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        validated_data['user_id'] = user_id
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id
        validated_data['status'] = InternSubmissionStatus.PENDING.value
        
        task = validated_data.get('task')
        task_status = validated_data.get('task_status')
        if task and task_status:
            task.status = task_status
            task.save()
            
        return super().create(validated_data)


class InternTimesheetHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InternDailyTimesheet
        fields = [
            'id', 'entry_date', 'task_id', 'category', 'description',
            'hours', 'blockers', 'task_status', 'remark',
            'end_of_day_note', 'edit_reason', 'status', 'karma_awarded',
            'review_note', 'created_at'
        ]
