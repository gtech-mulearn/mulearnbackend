import uuid
from django.db import models
from db.task import Organization, VoucherLog
from db.learning_circle import LearningCircle
from db.user import User
from db.task import TaskList
from django.conf import settings


class MuEvents(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    name = models.CharField(max_length=100, blank=False, null=False)
    description = models.CharField(max_length=500, blank=False, null=False)
    scheduled_time = models.DateTimeField(blank=False, null=False)
    assets = models.JSONField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=False, null=False)
    task_id = models.ForeignKey(
        TaskList,
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name="mu_events_task_id",
        db_column="task_id",
    )
    suggestions = models.CharField(max_length=500, blank=True, null=True)
    is_approved = models.BooleanField(null=True, blank=False)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        blank=False,
        null=True,
        related_name="mu_events_approved_by",
        db_column="approved_by",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        blank=False,
        null=False,
        related_name="mu_events_created_by",
        db_column="created_by",
    )
    org_id = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        blank=False,
        null=True,
        related_name="mu_events_org_id",
        db_column="org_id",
    )
    lc_id = models.ForeignKey(
        LearningCircle,
        on_delete=models.CASCADE,
        blank=False,
        null=True,
        related_name="mu_events_lc_id",
        db_column="lc_id",
    )
    ig_id = models.JSONField(blank=False, null=True)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "mu_events"


class MuEventsKarmaRequest(models.Model):
    ROLE_CHOICES = [
        ("participant", "Participant"),
        ("speaker", "Speaker"),
        ("organizer", "Organizer"),
    ]
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4())
    pow = models.JSONField(blank=False, null=False)
    event_id = models.ForeignKey(
        MuEvents,
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name="mu_events_karma_request_event_id",
        db_column="event_id",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="participant")
    karma = models.IntegerField(blank=False, null=False, default=0)
    is_approved = models.BooleanField(null=True, blank=False)
    is_appraiser_approved = models.BooleanField(null=True, blank=False)
    voucher_id = models.ForeignKey(
        VoucherLog,
        on_delete=models.CASCADE,
        blank=False,
        null=True,
        related_name="mu_events_karma_request_voucher_id",
        db_column="voucher_id",
    )
    suggestions = models.CharField(max_length=500, blank=False, null=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        blank=False,
        null=True,
        related_name="mu_events_karma_request_approved_by",
        db_column="approved_by",
    )
    approved_at = models.DateTimeField(blank=True, null=True)
    appraised_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        blank=False,
        null=True,
        related_name="event_karma_request_appraised_by",
        db_column="appraised_by",
    )
    appraised_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        blank=False,
        null=False,
        related_name="mu_events_karma_request_created_by",
        db_column="created_by",
    )
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "mu_events_karma_request"
