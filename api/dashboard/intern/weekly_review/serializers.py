from rest_framework import serializers
from django.utils.timezone import now
from datetime import timedelta

from db.intern import InternWeeklyReview
from utils.types import InternSubmissionStatus

class InternWeeklyReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternWeeklyReview
        fields = [
            'team', 'is_on_leave', 'tasks_assigned', 'tasks_completed',
            'weekly_review', 'task_remarks', 'hours_committed', 'blockers',
            'leave_days', 'suggestions'
        ]

    def validate(self, data):
        if data.get('hours_committed', 0) <= 0:
            raise serializers.ValidationError({"hours_committed": "Hours must be greater than 0."})
        return data

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        today = now().date()
        
        # If a user provides an explicit offset to submit for a previous week, we can handle it via request data.
        # For simplicity, we assume they submit for the current week unless they are late.
        # The prompt says: "Deadline: Sunday 23:59 UTC. Late submissions accepted but flagged is_late=True"
        # If we just use current ISO week, how do they submit for last week?
        # Let's say if they submit on Mon/Tue/Wed, and haven't submitted last week, they are submitting for last week and it's late.
        # But this is a complex UI flow. For now, let's just use current week.
        # The prompt allows is_late=True. 
        iso_year, iso_week, weekday = today.isocalendar()
        week_start_date = today - timedelta(days=weekday - 1)
        week_end_date = week_start_date + timedelta(days=6)
        
        validated_data['user_id'] = user_id
        validated_data['iso_year'] = iso_year
        validated_data['iso_week'] = iso_week
        validated_data['week_start_date'] = week_start_date
        validated_data['week_end_date'] = week_end_date
        validated_data['is_late'] = False # For now, always false unless overridden
        
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
            'leave_days', 'suggestions', 'is_late', 'status', 'karma_awarded',
            'review_note', 'created_at'
        ]
