from rest_framework import serializers
from django.db import transaction
from datetime import timedelta

from db.intern import InternDailyTimesheet, InternTask
from utils.types import InternSubmissionStatus, InternTaskStatus, COUNTED_TIMESHEET_STATUSES
from utils.utils import DateTimeUtils

from .streak import log_daily_timesheet_activity, sync_timesheet_streak

# Error code attached to the duplicate-date validation error so the view can
# answer 409 instead of a generic 400.
DUPLICATE_TIMESHEET_CODE = 'duplicate_timesheet'

# Timesheets count without admin review, so a minimum description length is
# the only guard against one-word entries. DRF trims leading/trailing
# whitespace before validators run, so padding doesn't count.
DESCRIPTION_MIN_LENGTH = 30
DESCRIPTION_MAX_LENGTH = 2000
DESCRIPTION_ERRORS = {
    'min_length': f"Description must be at least {DESCRIPTION_MIN_LENGTH} characters.",
}


class TaskUpdateEntrySerializer(serializers.Serializer):
    """Validates a single task entry inside the `task` JSON array."""
    task_id = serializers.CharField()
    status = serializers.ChoiceField(
        choices=[s.value for s in InternTaskStatus]
    )
    remark = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class InternTimesheetSerializer(serializers.ModelSerializer):
    task = TaskUpdateEntrySerializer(many=True, required=False, allow_null=True)
    description = serializers.CharField(
        min_length=DESCRIPTION_MIN_LENGTH, max_length=DESCRIPTION_MAX_LENGTH, error_messages=DESCRIPTION_ERRORS
    )
    blockers = serializers.CharField(max_length=1000, required=False, allow_blank=True, allow_null=True)
    end_of_day_note = serializers.CharField(max_length=1000, required=False, allow_blank=True, allow_null=True)
    # Accepted for backward compatibility with clients built on the old form
    # (unknown fields are rejected project-wide), but discarded: it only
    # justified late submissions, which are no longer allowed.
    edit_reason = serializers.CharField(
        max_length=300, required=False, allow_blank=True, allow_null=True, write_only=True
    )

    class Meta:
        model = InternDailyTimesheet
        fields = [
            'entry_date', 'task', 'description',
            'hours', 'blockers', 'end_of_day_note', 'edit_reason',
        ]

    def validate(self, data):
        entry_date = data.get('entry_date')
        # Day boundaries follow IST, not the server's UTC date.
        today = DateTimeUtils.get_ist_today()
        yesterday = today - timedelta(days=1)
        user_id = self.context.get('user_id')

        if entry_date > today:
            raise serializers.ValidationError({"entry_date": "Future dates are not allowed."})

        # No admin review any more, so a submission counts immediately —
        # only today and yesterday are accepted to prevent backfilling.
        if entry_date < yesterday:
            raise serializers.ValidationError(
                {"entry_date": "Timesheets can only be submitted for today or yesterday."}
            )

        if not data.get('description'):
            raise serializers.ValidationError({"description": "Description is required."})

        hours = data.get('hours', 0)
        if not hours or hours <= 0:
            raise serializers.ValidationError({"hours": "Hours must be greater than 0."})
        if hours > 24:
            raise serializers.ValidationError({"hours": "Hours cannot exceed 24 in a single day."})

        # Prevent duplicate timesheet for the same date
        if InternDailyTimesheet.objects.filter(user_id=user_id, entry_date=entry_date).exists():
            raise serializers.ValidationError(
                {"entry_date": "A timesheet for this date has already been submitted."},
                code=DUPLICATE_TIMESHEET_CODE,
            )

        task_entries = data.get('task') or []
        task_ids = [entry.get('task_id') for entry in task_entries if entry.get('task_id')]

        # Bulk fetch tasks
        intern_tasks = {
            str(t.id): t for t in InternTask.objects.filter(id__in=task_ids, assigned_to_id=user_id)
        }

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
            intern_task = intern_tasks.get(str(task_id))
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
        validated_data.pop('edit_reason', None)  # not stored on submit

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
            # Counts immediately — no admin approval step.
            validated_data['status'] = InternSubmissionStatus.SUBMITTED.value

            timesheet = InternDailyTimesheet.objects.create(**validated_data)

            # Quest Log entry, then streak / milestone karma / AT_RISK→ACTIVE —
            # what admin approval used to do, now on submit.
            log_daily_timesheet_activity(user_id)
            sync_timesheet_streak(user_id, actor_id=user_id)

            return timesheet


class InternTimesheetHistorySerializer(serializers.ModelSerializer):
    # Points awarded to the leaderboard score for this timesheet entry.
    # Counted timesheets (submitted, plus legacy approved/pending) earn
    # 25 pts each; rejected ones earn 0.
    score = serializers.SerializerMethodField()

    class Meta:
        model = InternDailyTimesheet
        fields = [
            'id', 'entry_date', 'task', 'description',
            'hours', 'blockers', 'end_of_day_note', 'edit_reason',
            'status', 'review_note', 'created_at', 'score'
        ]

    def get_score(self, obj):
        return 25 if obj.status in COUNTED_TIMESHEET_STATUSES else 0


class InternTimesheetEditSerializer(serializers.ModelSerializer):
    task = TaskUpdateEntrySerializer(many=True, required=False, allow_null=True)
    description = serializers.CharField(
        min_length=DESCRIPTION_MIN_LENGTH, max_length=DESCRIPTION_MAX_LENGTH,
        error_messages=DESCRIPTION_ERRORS, required=False,
    )
    blockers = serializers.CharField(max_length=1000, required=False, allow_blank=True, allow_null=True)
    end_of_day_note = serializers.CharField(max_length=1000, required=False, allow_blank=True, allow_null=True)
    edit_reason = serializers.CharField(max_length=300, required=True, allow_blank=False, allow_null=False)
    hours = serializers.DecimalField(max_digits=4, decimal_places=2, required=False)
    # entry_date is not editable: moving a timesheet to another date would
    # rewrite the streak. It is still accepted so clients that resend the
    # whole form keep working, but it must equal the current date.
    entry_date = serializers.DateField(required=False)

    class Meta:
        model = InternDailyTimesheet
        fields = [
            'entry_date', 'task', 'description',
            'hours', 'blockers', 'end_of_day_note', 'edit_reason',
        ]

    def validate(self, data):
        user_id = self.context.get('user_id')

        # 0. edit_reason is mandatory for all modifications
        if 'edit_reason' not in data or not data.get('edit_reason'):
            raise serializers.ValidationError({"edit_reason": "edit_reason is mandatory for all modifications."})

        # 1. entry_date cannot change
        if 'entry_date' in data:
            if data['entry_date'] != self.instance.entry_date:
                raise serializers.ValidationError({"entry_date": "entry_date cannot be changed."})
            data.pop('entry_date')

        # 2. Validate description if provided
        if 'description' in data and not data.get('description'):
            raise serializers.ValidationError({"description": "Description is required."})

        # 3. Validate hours if provided
        if 'hours' in data:
            hours = data.get('hours')
            if hours is None or hours <= 0:
                raise serializers.ValidationError({"hours": "Hours must be greater than 0."})
            if hours > 24:
                raise serializers.ValidationError({"hours": "Hours cannot exceed 24 in a single day."})

        # 4. Validate task entries if provided
        if 'task' in data:
            task_entries = data.get('task') or []
            task_ids = [entry.get('task_id') for entry in task_entries if entry.get('task_id')]
            
            # Bulk fetch tasks
            intern_tasks = {
                str(t.id): t for t in InternTask.objects.filter(id__in=task_ids, assigned_to_id=user_id)
            }
            
            seen_task_ids = set()
            for entry in task_entries:
                task_id = entry.get('task_id')
                status = entry.get('status')

                if task_id in seen_task_ids:
                    raise serializers.ValidationError(
                        {"task": f"Duplicate task_id '{task_id}' in submission."}
                    )
                seen_task_ids.add(task_id)

                intern_task = intern_tasks.get(str(task_id))
                if not intern_task:
                    raise serializers.ValidationError(
                        {"task": f"Task '{task_id}' is not assigned to you or does not exist."}
                    )

                if intern_task.is_verified:
                    raise serializers.ValidationError(
                        {"task": f"Task '{intern_task.title}' is already verified and cannot be modified."}
                    )

                if status == InternTaskStatus.COMPLETED.value and not intern_task.output_link:
                    raise serializers.ValidationError(
                        {"task": f"Task '{intern_task.title}' requires an output_link before marking COMPLETED. Use the task submit endpoint first."}
                    )

                # Enrich entry with title for the snapshot
                entry['title'] = intern_task.title

        return data
