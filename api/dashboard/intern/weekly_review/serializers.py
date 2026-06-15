from rest_framework import serializers
from django.utils.timezone import now
from datetime import timedelta

from db.intern import InternWeeklyReview
from utils.types import InternSubmissionStatus

class InternWeeklyReviewSerializer(serializers.ModelSerializer):
    week_start_date = serializers.DateField(required=False, write_only=True)
    rating = serializers.IntegerField(required=False, write_only=True)
    next_week_plan = serializers.CharField(required=False, write_only=True, allow_blank=True, allow_null=True)
    challenges_faced = serializers.CharField(required=False, write_only=True, allow_blank=True, allow_null=True)
    learnings = serializers.CharField(required=False, write_only=True, allow_blank=True, allow_null=True)

    class Meta:
        model = InternWeeklyReview
        fields = [
            'team', 'is_on_leave', 'tasks_assigned', 'tasks_completed',
            'weekly_review', 'task_remarks', 'hours_committed', 'blockers',
            'leave_days', 'suggestions', 'week_start_date', 'rating',
            'next_week_plan', 'challenges_faced', 'learnings'
        ]
        extra_kwargs = {
            'hours_committed': {'required': False, 'allow_null': True},
            'tasks_assigned': {'required': False, 'allow_null': True},
            'tasks_completed': {'required': False, 'allow_blank': True, 'allow_null': True},
            'weekly_review': {'required': False, 'allow_blank': True, 'allow_null': True},
        }

    def validate(self, data):
        # Determine is_on_leave (check input data, fallback to instance attribute if PATCH)
        is_on_leave = data.get('is_on_leave')
        if is_on_leave is None and self.instance:
            is_on_leave = self.instance.is_on_leave
        if is_on_leave is None:
            is_on_leave = False

        if not is_on_leave:
            # If not on leave, hours_committed must be > 0.
            if 'hours_committed' in data:
                val = data['hours_committed']
                if val is None or val <= 0:
                    raise serializers.ValidationError({"hours_committed": "Hours must be greater than 0."})
            elif not self.instance:
                raise serializers.ValidationError({"hours_committed": "Hours committed is required when not on leave."})
        else:
            # If on leave, hours_committed can be 0 or omitted.
            if 'hours_committed' in data:
                val = data['hours_committed']
                if val is None:
                    data['hours_committed'] = 0
            elif not self.instance:
                data['hours_committed'] = 0
        return data

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        today = now().date()
        
        target_date = validated_data.pop('week_start_date', None) or today
        iso_year, iso_week, weekday = target_date.isocalendar()
        week_start_date = target_date - timedelta(days=weekday - 1)
        week_end_date = week_start_date + timedelta(days=6)
        
        rating = validated_data.pop('rating', None)
        next_week_plan = validated_data.pop('next_week_plan', None)
        challenges_faced = validated_data.pop('challenges_faced', None)
        learnings = validated_data.pop('learnings', None)
        
        if 'task_remarks' not in validated_data:
            validated_data['task_remarks'] = {
                'rating': rating,
                'next_week_plan': next_week_plan,
                'challenges_faced': challenges_faced,
                'learnings': learnings
            }
            
        if 'weekly_review' not in validated_data or not validated_data.get('weekly_review'):
            parts = []
            if learnings:
                parts.append(f"Learnings: {learnings}")
            if challenges_faced:
                parts.append(f"Challenges Faced: {challenges_faced}")
            if next_week_plan:
                parts.append(f"Next Week Plan: {next_week_plan}")
            validated_data['weekly_review'] = "\n\n".join(parts) or "Weekly review submission"
            
        # Ensure non-nullable database fields have default values
        validated_data['tasks_assigned'] = validated_data.get('tasks_assigned') or {}
        validated_data['tasks_completed'] = validated_data.get('tasks_completed') or ""
        
        validated_data['user_id'] = user_id
        validated_data['iso_year'] = iso_year
        validated_data['iso_week'] = iso_week
        validated_data['week_start_date'] = week_start_date
        validated_data['week_end_date'] = week_end_date
        validated_data['is_late'] = False
        
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id
        validated_data['status'] = InternSubmissionStatus.PENDING.value
        
        return super().create(validated_data)


class InternWeeklyReviewHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InternWeeklyReview
        fields = [
            'id', 'iso_year', 'iso_week', 'week_start_date', 'week_end_date',
            'team', 'is_on_leave', 'tasks_assigned', 'tasks_completed',
            'weekly_review', 'task_remarks', 'hours_committed', 'blockers',
            'leave_days', 'suggestions', 'is_late', 'status',
            'review_note', 'created_at'
        ]
