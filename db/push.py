"""
Push notification tables (FCM). DDL: db-scripts alter-1.93.sql.
Design: docs/push-notifications.md
"""
import uuid

from django.db import models

from .user import User


def _uuid():
    return str(uuid.uuid4())


class UserPushDevice(models.Model):
    """One FCM registration token. A token belongs to whoever registered it
    last, so a phone shared between accounts never pushes to the old one."""

    class Platform(models.TextChoices):
        ANDROID = "android"
        IOS = "ios"
        WEB = "web"

    id = models.CharField(primary_key=True, max_length=36, default=_uuid)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column="user_id",
        related_name="push_devices",
    )
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=10, choices=Platform.choices)
    app_version = models.CharField(max_length=20, blank=True, null=True)
    timezone = models.CharField(max_length=40, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    failure_count = models.IntegerField(default=0)
    last_seen_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "user_push_device"


class UserPushPreference(models.Model):
    """Per-user switches. No row means the defaults (see api.push.config)."""

    user = models.OneToOneField(
        User, primary_key=True, on_delete=models.CASCADE, db_column="user_id",
        related_name="push_preference",
    )
    push_enabled = models.BooleanField(default=True)
    engagement_enabled = models.BooleanField(default=True)
    muted_categories = models.JSONField(default=list, blank=True)
    quiet_start = models.SmallIntegerField(default=22)
    quiet_end = models.SmallIntegerField(default=8)
    timezone = models.CharField(max_length=40, default="Asia/Kolkata")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "user_push_preference"


class PushDeliveryLog(models.Model):
    """One row per send decision. Caps, cooldowns, fatigue and stats read it."""

    class Source(models.TextChoices):
        ACTIVITY = "activity"
        ENGAGEMENT = "engagement"
        CAMPAIGN = "campaign"
        TEST = "test"

    class Status(models.TextChoices):
        SENT = "sent"
        FAILED = "failed"
        SKIPPED_DISABLED = "skipped_disabled"
        SKIPPED_PREF = "skipped_pref"
        SKIPPED_QUIET = "skipped_quiet"
        SKIPPED_CAP = "skipped_cap"
        SKIPPED_COOLDOWN = "skipped_cooldown"
        NO_DEVICE = "no_device"
        DEFERRED = "deferred"

    id = models.CharField(primary_key=True, max_length=36, default=_uuid)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column="user_id",
        related_name="push_deliveries",
    )
    source = models.CharField(max_length=12, choices=Source.choices)
    # Notification type for activity pushes, rule key for engagement.
    kind = models.CharField(max_length=50)
    campaign_id = models.CharField(max_length=36, blank=True, null=True)
    dedupe_key = models.CharField(max_length=160)
    status = models.CharField(max_length=20, choices=Status.choices)
    title = models.CharField(max_length=100)
    body = models.CharField(max_length=240)
    route = models.CharField(max_length=255, blank=True, null=True)
    device_count = models.SmallIntegerField(default=0)
    opened_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "push_delivery_log"


class PushCampaign(models.Model):
    """An admin-written push: audience, schedule and counters."""

    class Status(models.TextChoices):
        DRAFT = "draft"
        SCHEDULED = "scheduled"
        SENDING = "sending"
        SENT = "sent"
        CANCELLED = "cancelled"
        FAILED = "failed"

    id = models.CharField(primary_key=True, max_length=36, default=_uuid)
    title = models.CharField(max_length=100)
    body = models.CharField(max_length=240)
    route = models.CharField(max_length=255, blank=True, null=True)
    # {"type": "all" | "roles" | "igs" | "colleges" | "muids", "ids": [...]}
    audience = models.JSONField(default=dict)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    respect_quiet_hours = models.BooleanField(default=True)
    target_count = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, db_column="created_by",
        related_name="push_campaigns",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "push_campaign"


class PushConfig(models.Model):
    """Admin-tunable settings, one JSON value per key ('global', 'rule:<KEY>',
    'types'). Stored values override code defaults key by key."""

    key = models.CharField(primary_key=True, max_length=60)
    value = models.JSONField(default=dict)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, db_column="updated_by",
        related_name="push_config_updates",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "push_config"
