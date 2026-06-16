from rest_framework import serializers
from db.intern import InternWeeklyReview, InternDailyTimesheet

class ManageInternWeeklyReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    muid = serializers.CharField(source='user.muid', read_only=True)

    class Meta:
        model = InternWeeklyReview
        fields = [
            'id', 'user_id', 'user_name', 'muid', 'iso_year', 'iso_week', 'week_start_date', 'week_end_date',
            'team', 'is_on_leave', 'tasks_assigned', 'tasks_completed',
            'weekly_review', 'task_remarks', 'hours_committed', 'blockers',
            'leave_days', 'suggestions', 'is_late', 'status',
            'review_note', 'created_at'
        ]

class ManageInternTimesheetSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    muid = serializers.CharField(source='user.muid', read_only=True)

    class Meta:
        model = InternDailyTimesheet
        fields = [
            'id', 'user_id', 'user_name', 'muid', 'entry_date', 'task', 'description',
            'hours', 'blockers', 'end_of_day_note', 'edit_reason', 'status',
            'review_note', 'created_at'
        ]
