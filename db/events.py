import uuid

from django.db import models
from django.conf import settings

from .user import User


class MediaContent(models.Model):
    """
    Unified model for CMS-migrated content types:
      - Office Hours sessions
      - Salt Mango Tree episodes
      - Inspiration Station Radio episodes

    The ``content_type`` field acts as a discriminator. Type-specific
    fields are nullable and only populated for the relevant type.
    Soft-delete is supported via ``deleted_at``.
    """

    class ContentType(models.TextChoices):
        OFFICE_HOURS        = 'office_hours',         'Office Hours'
        SALT_MANGO_TREE     = 'salt_mango_tree',      'Salt Mango Tree'
        INSPIRATION_STATION = 'inspiration_station',  'Inspiration Station Radio'

    class Zone(models.TextChoices):
        NORTH   = 'north',   'North'
        CENTRAL = 'central', 'Central'
        SOUTH   = 'south',   'South'

    # ── Primary key ───────────────────────────────────────────────────────────
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)

    # ── Discriminator ─────────────────────────────────────────────────────────
    content_type = models.CharField(
        max_length=30, choices=ContentType.choices, db_index=True
    )

    # ── Shared fields (all types) ─────────────────────────────────────────────
    # Office Hours uses "title"; SMT & Inspiration Station use "topic" —
    # both are stored in this single column.
    title       = models.CharField(max_length=300)
    date        = models.DateField()
    description = models.TextField(blank=True, null=True)
    link        = models.CharField(max_length=500, blank=True, null=True)

    # ── Office Hours specific ─────────────────────────────────────────────────
    performer        = models.CharField(max_length=200, blank=True, null=True)
    designation      = models.CharField(max_length=200, blank=True, null=True)
    interest_groups  = models.JSONField(blank=True, null=True)   # list of IG slugs
    poster_thumbnail = models.CharField(max_length=512, blank=True, null=True)

    # ── SMT & Inspiration Station specific ────────────────────────────────────
    campus = models.CharField(max_length=200, blank=True, null=True)
    zone   = models.CharField(
        max_length=10, choices=Zone.choices, blank=True, null=True
    )

    # ── Soft delete ───────────────────────────────────────────────────────────
    deleted_at = models.DateTimeField(blank=True, null=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='created_by', related_name='media_content_created_by'
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='updated_by', related_name='media_content_updated_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'media_content'
        indexes = [
            models.Index(fields=['content_type', 'date']),
        ]
