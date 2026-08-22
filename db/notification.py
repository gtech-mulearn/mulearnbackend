import uuid

from django.db import models
from django.conf import settings

from db.user import User

# fmt: off
# noinspection PyPep8


class Notification(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Who receives this notification
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")

    # ── What happened ──────────────────────────────────────────────────────────
    # type:     which specific event — one of 42 NotificationType values
    #           old rows carry "LEGACY", new rows always have a real type
    # category: which product module — derived from type by dispatch()
    #           never set by a producer directly
    type        = models.CharField(max_length=50,  default="LEGACY")
    category    = models.CharField(max_length=20,  default="SYSTEM")

    # ── What to show ───────────────────────────────────────────────────────────
    title       = models.CharField(max_length=100)
    description = models.CharField(max_length=300)

    # ── Raw producer variables ─────────────────────────────────────────────────
    # Stored so future channels (email, push) can re-render without a schema change
    context     = models.JSONField(null=True, blank=True)

    # ── What the notification is about (powers frontend deep-linking) ──────────
    entity_type = models.CharField(max_length=40,  null=True, blank=True)
    entity_id   = models.CharField(max_length=36,  null=True, blank=True)

    # ── Who triggered the action ───────────────────────────────────────────────
    # SET_NULL so deleting a user never orphans notification rows
    actor       = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        db_column="actor_id", related_name="caused_notifications"
    )

    # ── Read state ─────────────────────────────────────────────────────────────
    is_read     = models.BooleanField(default=False)
    read_at     = models.DateTimeField(null=True, blank=True)

    # ── Soft hide ──────────────────────────────────────────────────────────────
    is_archived = models.BooleanField(default=False)

    # ── Duplicate prevention ───────────────────────────────────────────────────
    # Format: "type:entity_id:occurrence"
    # DB has UNIQUE INDEX on (user_id, dedupe_key) — bulk_create(ignore_conflicts=True)
    # silently rejects duplicates without crashing
    dedupe_key  = models.CharField(max_length=160, null=True, blank=True)

    # ── Admin broadcast only ───────────────────────────────────────────────────
    redirect_url = models.CharField(max_length=255, null=True, blank=True)
    batch_id     = models.CharField(max_length=36,  null=True, blank=True)

    # ── Legacy fields — do not use in new code ─────────────────────────────────
    button      = models.CharField(max_length=10,  blank=True, null=True)
    url         = models.CharField(max_length=100, blank=True, null=True)

    # ── Audit ──────────────────────────────────────────────────────────────────
    created_at  = models.DateTimeField(auto_now_add=True)
    created_by  = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column="created_by", related_name="created_notifications"
    )

    class Meta:
        managed  = False
        db_table = "notification"
        ordering = ["-created_at"]   # newest-first (old ascending order was a bug)


class BroadcastNotification(models.Model):
    """
    LEGACY — pre-v2 broadcast system. Do not use for new code.
    New broadcasts go through NotificationService.dispatch() with ADMIN_BROADCAST type.
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
        managed  = False
        db_table = "broadcast_notification"
        ordering = ["-created_at"]
