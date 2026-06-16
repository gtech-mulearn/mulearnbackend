import uuid

from django.db import models

from .user import User


class UserInternGuildLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='intern_guild_link')
    guild = models.CharField(max_length=75)
    status = models.CharField(max_length=15, default='ACTIVE')
    previous_status = models.CharField(max_length=15, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intern_guild_created', db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intern_guild_updated', db_column='updated_by')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'user_intern_guild_link'


class InternTask(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    title = models.CharField(max_length=150)
    description = models.TextField()
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_intern_tasks', db_column='assigned_to')
    team = models.CharField(max_length=75)
    category = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default='NOT_STARTED')
    complexity = models.CharField(max_length=10, default='LOW')
    deadline = models.DateField()
    iso_week = models.IntegerField()
    is_archived = models.BooleanField(default=False)
    karma_awarded = models.IntegerField(default=0)
    output_link = models.URLField(max_length=500, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='intern_task_verified', db_column='verified_by_id')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intern_task_created', db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intern_task_updated', db_column='updated_by')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'intern_task'


class InternDailyTimesheet(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intern_daily_timesheets', db_column='user_id')
    entry_date = models.DateField()
    # task: JSON array of {task_id, title, status, remark} — updated per submission
    task = models.JSONField(null=True, blank=True)
    description = models.TextField()
    hours = models.DecimalField(max_digits=4, decimal_places=2)
    blockers = models.TextField(null=True, blank=True)
    end_of_day_note = models.TextField(null=True, blank=True)
    edit_reason = models.CharField(max_length=300, null=True, blank=True)
    status = models.CharField(max_length=15, default='PENDING')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='intern_timesheet_reviews', db_column='reviewed_by')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=300, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intern_timesheet_created', db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intern_timesheet_updated', db_column='updated_by')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'intern_daily_timesheet'


class InternWeeklyReview(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intern_weekly_reviews', db_column='user_id')
    iso_year = models.SmallIntegerField()
    iso_week = models.IntegerField()
    week_start_date = models.DateField()
    week_end_date = models.DateField()
    team = models.CharField(max_length=75)
    is_on_leave = models.BooleanField(default=False)
    tasks_assigned = models.JSONField(default=dict)
    # tasks_completed: JSON array of {task_id, title, category, complexity, deadline, final_status, output_link}
    tasks_completed = models.JSONField(null=True, blank=True)
    weekly_review = models.TextField()
    task_remarks = models.JSONField(null=True, blank=True)
    hours_committed = models.DecimalField(max_digits=5, decimal_places=2)
    blockers = models.TextField(null=True, blank=True)
    leave_days = models.TextField(null=True, blank=True)
    suggestions = models.TextField(null=True, blank=True)
    is_late = models.BooleanField(default=False)
    status = models.CharField(max_length=15, default='PENDING')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='intern_weekly_reviews_reviewed', db_column='reviewed_by')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=300, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intern_weekly_review_created', db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intern_weekly_review_updated', db_column='updated_by')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'intern_weekly_review'


class InternLeaveRequest(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intern_leave_requests', db_column='user_id')
    leave_type = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.SmallIntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=15, default='PENDING')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='intern_leave_reviews', db_column='reviewed_by')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=300, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intern_leave_created', db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intern_leave_updated', db_column='updated_by')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'intern_leave_request'
