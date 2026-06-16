from rest_framework import serializers
from django.utils.timezone import now
from django.db import transaction
from datetime import timedelta

from db.intern import InternDailyTimesheet, InternTask
from utils.types import InternSubmissionStatus, InternTaskStatus


class TaskUpdateEntrySerializer(serializers.Serializer):
    """Validates a single task entry inside the `task` JSON array."""
    task_id = serializers.CharField()
    status = serializers.ChoiceField(
        choices=[s.value for s in InternTaskStatus]
    )
    remark = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class InternTimesheetSerializer(serializers.ModelSerializer):
    task = TaskUpdateEntrySerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = InternDailyTimesheet
        fields = [
            'entry_date', 'task', 'description',
            'hours', 'blockers', 'end_of_day_note', 'edit_reason',
        ]

    def validate(self, data):
        entry_date = data.get('entry_date')
        today = now().date()
        yesterday = today - timedelta(days=1)

        if entry_date > today:
            raise serializers.ValidationError({"entry_date": "Future dates are not allowed."})

        if entry_date < yesterday and not data.get('edit_reason'):
            raise serializers.ValidationError({"edit_reason": "Reason is required for late submissions."})

        if not data.get('description'):
            raise serializers.ValidationError({"description": "Description is required."})

        if not data.get('hours') or data.get('hours', 0) <= 0:
            raise serializers.ValidationError({"hours": "Hours must be greater than 0."})

        task_entries = data.get('task') or []
        user_id = self.context.get('user_id')

        seen_task_ids = set()
        for entry in task_entries:
            task_id = entry.get('task_id')
            status = entry.get('status')

            # Duplicate task_id in same submission
            if task_id in seen_task_ids:
                raise serializers.ValidationError(
                    {"task": f"Duplicate task_id '{task_id}' in submission."}
                )
            seen_task_ids.add(task_id)

            # Must belong to this intern
            intern_task = InternTask.objects.filter(id=task_id, assigned_to_id=user_id).first()
            if not intern_task:
                raise serializers.ValidationError(
                    {"task": f"Task '{task_id}' is not assigned to you or does not exist."}
                )

            # Cannot modify verified task
            if intern_task.is_verified:
                raise serializers.ValidationError(
                    {"task": f"Task '{intern_task.title}' is already verified and cannot be modified."}
                )

            # COMPLETED requires output_link to already be set
            if status == InternTaskStatus.COMPLETED.value and not intern_task.output_link:
                raise serializers.ValidationError(
                    {"task": f"Task '{intern_task.title}' requires an output_link before marking COMPLETED. Use the task submit endpoint first."}
                )

            # Enrich entry with title for the snapshot
            entry['title'] = intern_task.title

        return data

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        task_entries = validated_data.pop('task', None) or []

        with transaction.atomic():
            # Update InternTask.status for each entry
            for entry in task_entries:
                task_id = entry.get('task_id')
                new_status = entry.get('status')
                InternTask.objects.filter(id=task_id, assigned_to_id=user_id).update(status=new_status)

            # Store clean snapshot (task_id, title, status, remark)
            snapshot = [
                {
                    'task_id': e['task_id'],
                    'title': e.get('title', ''),
                    'status': e['status'],
                    'remark': e.get('remark') or '',
                }
                for e in task_entries
            ] or None

            validated_data['task'] = snapshot
            validated_data['user_id'] = user_id
            validated_data['created_by_id'] = user_id
            validated_data['updated_by_id'] = user_id
            validated_data['status'] = InternSubmissionStatus.PENDING.value

            return InternDailyTimesheet.objects.create(**validated_data)


class InternTimesheetHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InternDailyTimesheet
        fields = [
            'id', 'entry_date', 'task', 'description',
            'hours', 'blockers', 'end_of_day_note', 'edit_reason',
            'status', 'review_note', 'created_at'
        ]
