from django.db import models
import uuid
from db.task import Level, InterestGroup
from db.user import User


class Achievement(models.Model):
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36)
    name = models.CharField(max_length=75, unique=True)
    level_id = models.ForeignKey(Level, on_delete=models.CASCADE, db_column="level_id", null=True, blank=True)
    description = models.CharField(max_length=300)
    icon = models.CharField(max_length=100)
    has_vc = models.BooleanField()
    tags = models.JSONField()
    type = models.CharField(max_length=36)
    template_id = models.CharField(max_length=100, null=True, blank=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="achievements_updated_by",
        db_column="updated_by",
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="achievements_created_by",
        db_column="created_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "achievement"
        managed = False


class UserAchievementsLog(models.Model):
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36)
    user_id = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        related_name="achievements",
        db_column="user_id",
        db_index=True,
    )
    achievement_id = models.ForeignKey(
        "Achievement",
        on_delete=models.CASCADE,
        related_name="users",
        db_column="achievement_id",
        db_index=True,
    )
    rule_version = models.IntegerField(default=1)
    is_issued = models.BooleanField(default=False)
    vc_url = models.CharField(max_length=100, blank=True, default="")
    updated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_achievements_updated_by",
        db_column="updated_by",
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_achievements_created_by",
        db_column="created_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_achievements_log"
        managed = False
        unique_together = [["user_id", "achievement_id"]]


# ============================================================================
# NEW MODELS FOR ACHIEVEMENT SYSTEM
# ============================================================================


class AchievementEvent(models.Model):
    """Canonical events for achievement evaluation - immutable, append-only"""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36)
    event_id = models.CharField(max_length=36, unique=True)  # Idempotency key
    event_type = models.CharField(max_length=50)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="achievement_events",
        db_column="user_id",
    )
    region = models.CharField(max_length=50, null=True, blank=True)
    metadata = models.JSONField()
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "achievement_event"
        managed = False


class AchievementRule(models.Model):
    """Versioned rules for achievement eligibility - immutable once created"""
    RULE_TYPE_CHOICES = [
        ("ig_karma", "IG Karma Threshold"),
        ("skill", "Skill Task Count"),
        ("streak", "Daily Streak"),
        ("milestone", "Total Milestone"),
        ("event", "Event Attendance"),
    ]

    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36)
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name="rules",
        db_column="achievement_id",
    )
    version = models.IntegerField(default=1)
    rule_type = models.CharField(max_length=30, choices=RULE_TYPE_CHOICES)
    conditions = models.JSONField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="achievement_rules_created",
        db_column="created_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "achievement_rule"
        managed = False
        unique_together = [["achievement", "version"]]


class UserSkillProgress(models.Model):
    """Pre-aggregated skill progress for O(1) eligibility checks"""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="skill_progress",
        db_column="user_id",
    )
    skill_id = models.CharField(max_length=36)  # IG id or custom skill id
    completed_task_count = models.IntegerField(default=0)
    total_karma = models.IntegerField(default=0)
    last_task_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_skill_progress"
        managed = False
        unique_together = [["user", "skill_id"]]


class UserIgKarma(models.Model):
    """Pre-aggregated karma per user+IG for fast lookups"""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ig_karma",
        db_column="user_id",
    )
    ig = models.ForeignKey(
        InterestGroup,
        on_delete=models.CASCADE,
        related_name="user_karma",
        db_column="ig_id",
    )
    total_karma = models.IntegerField(default=0)
    task_count = models.IntegerField(default=0)
    last_activity = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_ig_karma"
        managed = False
        unique_together = [["user", "ig"]]


class UserDailyActivity(models.Model):
    """Daily activity tracking - source of truth for streaks"""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="daily_activities",
        db_column="user_id",
    )
    activity_date = models.DateField()
    has_task = models.BooleanField(default=False)
    has_karma = models.BooleanField(default=False)
    has_login = models.BooleanField(default=False)
    task_count = models.IntegerField(default=0)
    karma_earned = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_daily_activity"
        managed = False
        unique_together = [["user", "activity_date"]]


class UserStreak(models.Model):
    """Streak tracking derived from daily activity"""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="streaks",
        db_column="user_id",
    )
    streak_type = models.CharField(max_length=30)  # daily_login, daily_task
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_active = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_streak"
        managed = False
        unique_together = [["user", "streak_type"]]


class AchievementAuditLog(models.Model):
    """Full audit trail for achievements - for debugging and compliance"""
    ACTION_CHOICES = [
        ("issued", "Achievement Issued"),
        ("revoked", "Achievement Revoked"),
        ("vc_issued", "VC Issued"),
        ("vc_failed", "VC Issuance Failed"),
    ]

    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="achievement_audit_logs",
        db_column="user_id",
    )
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        db_column="achievement_id",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    rule_version = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    performed_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="audit_logs_performed",
        db_column="performed_by",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "achievement_audit_log"
        managed = False

