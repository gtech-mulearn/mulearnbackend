from rest_framework import serializers
from db.intern import InternWeeklyReview, InternDailyTimesheet, InternMonthlyReview
from api.dashboard.intern.monthly_review.leave import review_leave_days

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

class ManageInternMonthlyReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    muid = serializers.CharField(source='user.muid', read_only=True)
    # Approved leave days in the review month (WFH included), worked out on
    # read. The list view passes context['leave_days'] from leave_days_by_review.
    leave_days = serializers.SerializerMethodField()

    class Meta:
        model = InternMonthlyReview
        fields = [
            'id', 'user_id', 'user_name', 'muid', 'year', 'month', 'period_start', 'period_end',
            'team', 'tasks_completed', 'monthly_review', 'task_remarks', 'blockers',
            'leave_days', 'suggestions', 'status', 'reviewed_by_id', 'reviewed_at',
            'review_note', 'created_at', 'updated_at',
        ]

    def get_leave_days(self, obj) -> int:
        return review_leave_days(self, obj)

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
