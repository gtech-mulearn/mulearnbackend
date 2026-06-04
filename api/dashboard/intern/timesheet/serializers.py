from rest_framework import serializers
from django.utils.timezone import now
from datetime import timedelta

from db.intern import InternDailyTimesheet, InternTask
from utils.types import InternSubmissionStatus

class InternTimesheetSerializer(serializers.ModelSerializer):
    log_description = serializers.CharField(required=False, write_only=True)
    hours_worked = serializers.DecimalField(max_digits=4, decimal_places=2, required=False, write_only=True)

    class Meta:
        model = InternDailyTimesheet
        fields = [
            'entry_date', 'task', 'category', 'description',
            'hours', 'blockers', 'task_status', 'remark',
            'end_of_day_note', 'edit_reason', 'log_description', 'hours_worked'
        ]

    def validate(self, data):
        log_description = data.pop('log_description', None)
        if log_description:
            data['description'] = log_description
            
        hours_worked = data.pop('hours_worked', None)
        if hours_worked is not None:
            data['hours'] = hours_worked
            
        if not data.get('description'):
            raise serializers.ValidationError({"description": "Description (or log_description) is required."})
            
        if not data.get('hours'):
            raise serializers.ValidationError({"hours": "Hours (or hours_worked) is required."})

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
