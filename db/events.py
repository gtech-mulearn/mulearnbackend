import uuid
from django.db import models
from db.task import Organization, VoucherLog
from db.learning_circle import LearningCircle
from db.user import User
from db.task import TaskList
from django.conf import settings


class Event(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4())
    name = models.CharField(max_length=100, blank=False, null=False)
    description = models.CharField(max_length=500, blank=False, null=False)
    assets = models.JSONField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=False, null=False)
    task_id = models.ForeignKey(
        TaskList,
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name="event_task_id",
    )
    suggestions = models.CharField(max_length=500, blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column="approved_by",
        blank=False,
        null=True,
        related_name="event_approved_by",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column="created_by",
        blank=False,
        null=False,
        related_name="event_created_by",
    )
    org_id = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        blank=False,
        null=True,
        related_name="event_org_id",
    )
    lc_id = models.ForeignKey(
        LearningCircle,
        on_delete=models.CASCADE,
        blank=False,
        null=True,
        related_name="event_lc_id",
    )
    ig_id = models.JSONField(blank=False, null=True)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "event"


class EventKarmaRequest(models.Model):
    ROLE_CHOICES = [
        ("participant", "Participant"),
        ("speaker", "Speaker"),
        ("organizer", "Organizer"),
    ]
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4())
    pow = models.JSONField(blank=False, null=False)
    event_id = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name="event_karma_request_event_id",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="participant")
    karma = models.IntegerField(blank=False, null=False, default=0)
    is_approved = models.BooleanField(default=False)
    voucher_id = models.ForeignKey(
        VoucherLog,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="event_karma_request_voucher_id",
    )
    suggestions = models.CharField(max_length=500, blank=True, null=True)
    appraised_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column="appraised_by",
        blank=True,
        null=True,
        related_name="event_karma_request_appraised_by",
    )
    appraised_at = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column="approved_by",
        blank=True,
        null=True,
        related_name="event_karma_request_approved_by",
    )
    approved_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column="created_by",
        blank=False,
        null=False,
        related_name="event_karma_request_created_by",
    )
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "event_karma_request"
