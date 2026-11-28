import uuid

from django.conf import settings
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


class InternTeam(models.Model):
    """
    An intern team (e.g. Frontend). `name` may repeat; `code` is unique across
    every team, active or not, and is what Excel uploads match on. Teams are never
    deleted: they are deactivated (is_active=False) and can be activated again.
    """
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    name = models.CharField(max_length=75)
    code = models.CharField(max_length=10)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='intern_teams_deactivated', db_column='deactivated_by'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        related_name='intern_teams_created', db_column='created_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        related_name='intern_teams_updated', db_column='updated_by'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'intern_teams'


class UserInternTeamLink(models.Model):
    """
    One stint of an intern in one team. A person has one row per team they were
    in; is_current is True on the row they're in now and False on ended rows
    (history). The code keeps at most one current row per person (it locks all of
    a person's rows before creating or ending one; the DB index isn't unique).

    intern_status (InternStatus) is the person's standing in the stint:
    - current + INACTIVE: marked inactive by a Lead/Admin or the cron; still a
      member and still holds the intern roles.
    - ended (is_current False, INACTIVE): deactivated (roles removed) or moved to
      another team; exit_reason says which.
    A Lead is a member who also holds the Intern Lead role.
    """
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intern_team_links')
    # PROTECT matches the table's ON DELETE RESTRICT; teams are never deleted anyway.
    team = models.ForeignKey(
        InternTeam, on_delete=models.PROTECT, related_name='members', db_column='team_id'
    )
    intern_status = models.CharField(max_length=15, default='ACTIVE')
    previous_intern_status = models.CharField(max_length=15, null=True, blank=True)
    # Why intern_status last changed (optional text from the Lead/Admin).
    status_reason = models.CharField(max_length=300, null=True, blank=True)
    # Why the row ended: typed on deactivation, set by the code on reassign / role removal.
    exit_reason = models.CharField(max_length=300, null=True, blank=True)
    is_current = models.BooleanField(default=True)
    # The tenure, set by whoever adds the intern. While current, end_date is the
    # planned end; once the row ends it is the actual last day.
    join_date = models.DateField()
    end_date = models.DateField()
    created_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        related_name='intern_team_link_created', db_column='created_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        related_name='intern_team_link_updated', db_column='updated_by'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'user_intern_team_link'


class InternTask(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    title = models.CharField(max_length=150)
    description = models.TextField()
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_intern_tasks', db_column='assigned_to')
    # The team this was created in (NULL on rows from before teams).
    team = models.ForeignKey(
        InternTeam, on_delete=models.PROTECT, null=True, blank=True,
        related_name='tasks', db_column='team_id'
    )
    category = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default='NOT_STARTED')
    complexity = models.CharField(max_length=10, default='LOW')
    deadline = models.DateField()
    iso_week = models.IntegerField()
    is_archived = models.BooleanField(default=False)
    karma_awarded = models.IntegerField(default=0)
    output_link = models.URLField(max_length=500, null=True, blank=True)
    remark = models.TextField(null=True, blank=True)
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
    # The team this was created in (NULL on rows from before teams).
    team = models.ForeignKey(
        InternTeam, on_delete=models.PROTECT, null=True, blank=True,
        related_name='timesheets', db_column='team_id'
    )
    entry_date = models.DateField()
    # task: JSON array of {task_id, title, status, remark} — updated per submission
    task = models.JSONField(null=True, blank=True)
    description = models.TextField()
    hours = models.DecimalField(max_digits=4, decimal_places=2)
    blockers = models.TextField(null=True, blank=True)
    end_of_day_note = models.TextField(null=True, blank=True)
    edit_reason = models.CharField(max_length=300, null=True, blank=True)
    # No status column: timesheets are not approved, every submitted one counts.
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


class InternMonthlyReview(models.Model):
    """
    One review per intern per calendar month, submitted inside the month-end
    window (see api/dashboard/intern/monthly_review/window.py). Replaces the
    weekly review; there is no streak, no hours and no late flag.
    """
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intern_monthly_reviews', db_column='user_id')
    # The team this was created in (NULL on rows from before teams).
    team = models.ForeignKey(
        InternTeam, on_delete=models.PROTECT, null=True, blank=True,
        related_name='monthly_reviews', db_column='team_id'
    )
    year = models.SmallIntegerField()
    month = models.SmallIntegerField()
    period_start = models.DateField()
    period_end = models.DateField()
    # tasks_completed: JSON array of {task_id, title, category, complexity, deadline, final_status, output_link}
    tasks_completed = models.JSONField(null=True, blank=True)
    monthly_review = models.TextField()
    # task_remarks: {rating, learnings, challenges_faced, next_month_plan}
    task_remarks = models.JSONField(null=True, blank=True)
    blockers = models.TextField(null=True, blank=True)
    # No leave_days column: the API works it out on read from APPROVED
    # InternLeaveRequest rows clipped to the month
    # (api/dashboard/intern/monthly_review/leave.py).
    suggestions = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=15, default='PENDING')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='intern_monthly_reviews_reviewed', db_column='reviewed_by')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=300, null=True, blank=True)
    # Audit columns: deleting the user who last touched a review (e.g. the lead
    # who approved it) must not delete the intern's review.
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), related_name='intern_monthly_review_created', db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), related_name='intern_monthly_review_updated', db_column='updated_by')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'intern_monthly_review'


class InternLeaveRequest(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intern_leave_requests', db_column='user_id')
    # The team this was created in (NULL on rows from before teams).
    team = models.ForeignKey(
        InternTeam, on_delete=models.PROTECT, null=True, blank=True,
        related_name='leave_requests', db_column='team_id'
    )
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


class InternGuildMinute(models.Model):
    """
    Stores daily guild minutes uploaded by an Intern Lead.
    Each entry is scoped to a specific guild and date.
    """
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    guild = models.CharField(max_length=75)
    date = models.DateField()
    title = models.CharField(max_length=200)
    minutes = models.TextField()
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='intern_minutes_created', db_column='created_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='intern_minutes_updated', db_column='updated_by'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'intern_guild_minute'


class InternHistory(models.Model):
    """
    Append-only log of what an Admin or Lead did to an intern (onboarded, status
    changed, Lead added/removed, deactivated, reassigned). entity_type/entity_id
    point at the row acted on (MEMBERSHIP = user_intern_team_link); there is no FK
    on entity_id because it can point at different tables. Rows are never updated
    or deleted by the code. The daily cron is not recorded (there is no actor).
    """
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    entity_type = models.CharField(max_length=30)
    entity_id = models.CharField(max_length=36)
    action = models.CharField(max_length=30)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True,
        related_name='intern_history', db_column='user_id'
    )
    # The team after the action; from_team only when the team changed (reassign).
    team = models.ForeignKey(
        InternTeam, on_delete=models.PROTECT, null=True, blank=True,
        related_name='history', db_column='team_id'
    )
    from_team = models.ForeignKey(
        InternTeam, on_delete=models.PROTECT, null=True, blank=True,
        related_name='history_moved_from', db_column='from_team_id'
    )
    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    reason = models.CharField(max_length=300, null=True, blank=True)
    # Null for cron events (action_by_role SYSTEM): there is no system-user
    # convention for crons. The DB column is ON DELETE RESTRICT; deleting the actor
    # through Django moves their rows to the system admin first, as with the other
    # audit columns.
    action_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), null=True,
        related_name='intern_history_actions', db_column='action_by'
    )
    action_by_role = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'intern_history'
