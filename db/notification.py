import uuid

from django.db import models

from db.user import User

from django.conf import settings

# fmt: off
# noinspection PyPep8

class Notification(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title       = models.CharField(max_length=50, blank=False)
    description = models.CharField(max_length=200, blank=False)
    button      = models.CharField(max_length=10, blank=True, null=True)
    url         = models.CharField(max_length=100, blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    created_by  = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by", related_name="created_notifications")

    class Meta:
        managed = False
        db_table = "notification"
        ordering = ["created_at"]


class BroadcastNotification(models.Model):
    """
    One row per group-wide broadcast announcement.
    Recipients are resolved dynamically at read time via target_type + target_id.

    target_type values:
        'campus'          → all users linked to target_id (org_id)
        'interest_group'  → all learners with an active link to target_id (ig_id)
        'campus_ig'       → all learners in a campus-IG chapter (target_id = campus_ig composite id)
        'event_interest'  → all users who expressed interest in target_id (event_id)
        'event_coowners'  → event creator + all co-owners of target_id (event_id)
        'global'          → all active users (target_id is NULL)
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title       = models.CharField(max_length=50)
    description = models.CharField(max_length=200)
    url         = models.CharField(max_length=100, blank=True, null=True)
    target_type = models.CharField(max_length=30)
    target_id   = models.CharField(max_length=36,  blank=True, null=True)
    created_by  = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by", related_name="created_broadcasts")
    created_at  = models.DateTimeField()
    expires_at  = models.DateTimeField()

    class Meta:
        managed = False
        db_table  = "broadcast_notification"
        ordering  = ["-created_at"]
