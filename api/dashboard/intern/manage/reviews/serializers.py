from rest_framework import serializers
from db.intern import InternWeeklyReview, InternDailyTimesheet, InternMonthlyReview
from api.dashboard.intern.monthly_review.leave import review_leave_days
from utils.intern_permissions import team_ref, user_ref

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
    # The team the review was submitted in (null before teams) and who reviewed it.
    team = serializers.SerializerMethodField()
    reviewed_by = serializers.SerializerMethodField()

    class Meta:
        model = InternMonthlyReview
        fields = [
            'id', 'user_id', 'user_name', 'muid', 'year', 'month', 'period_start', 'period_end',
            'team', 'tasks_completed', 'monthly_review', 'task_remarks', 'blockers',
            'leave_days', 'suggestions', 'status', 'reviewed_by', 'reviewed_at',
            'review_note', 'created_at', 'updated_at',
        ]

    def get_leave_days(self, obj) -> int:
        return review_leave_days(self, obj)

    def get_team(self, obj):
        return team_ref(obj.team)

    def get_reviewed_by(self, obj):
        return user_ref(obj.reviewed_by)

class ManageInternTimesheetSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    muid = serializers.CharField(source='user.muid', read_only=True)
    # The team the timesheet was submitted in (null on timesheets from before teams).
    team = serializers.SerializerMethodField()
    # Who wrote review_note: {id, full_name, muid}, or null.
    reviewed_by = serializers.SerializerMethodField()

    class Meta:
        model = InternDailyTimesheet
        fields = [
            'id', 'user_id', 'user_name', 'muid', 'entry_date', 'task', 'description',
            'hours', 'blockers', 'end_of_day_note', 'edit_reason',
            'review_note', 'reviewed_by', 'reviewed_at', 'team', 'created_at'
        ]

    def get_team(self, obj):
        return team_ref(obj.team)

    def get_reviewed_by(self, obj):
        return user_ref(obj.reviewed_by)
