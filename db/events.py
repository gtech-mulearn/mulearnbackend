import uuid

from django.db import models
from django.conf import settings

from .user import User
from .task import Category, InterestGroup
from .organization import Organization


class Event(models.Model):

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING_CAMPUS_APPROVAL = 'PENDING_CAMPUS_APPROVAL', 'Pending_Campus_Approval'
        PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending_Approval'
        PENDING_MENTOR_APPROVAL = 'PENDING_MENTOR_APPROVAL', 'Pending_Mentor_Approval'
        PUBLISHED = 'PUBLISHED', 'Published'
        ONGOING = 'ONGOING', 'Ongoing'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        REJECTED = 'REJECTED', 'Rejected'

    class VenueType(models.TextChoices):
        PHYSICAL = 'PHYSICAL', 'Physical'
        ONLINE = 'ONLINE', 'Online'
        HYBRID = 'HYBRID', 'Hybrid'

    class Scope(models.TextChoices):
        GLOBAL = 'GLOBAL', 'Global'
        CAMPUS = 'CAMPUS', 'Campus'
        IG = 'IG', 'Interest Group'
        CAMPUS_IG = 'CAMPUS_IG', 'Campus_IG'
        COMPANY = 'COMPANY', 'Company'

    class OrganiserType(models.TextChoices):
        GLOBAL_IG = 'GLOBAL_IG', 'Global_IG'
        CAMPUS_IG = 'CAMPUS_IG', 'Campus_IG'
        CAMPUS = 'CAMPUS', 'Campus'
        COMPANY = 'COMPANY', 'Company'
        ADMIN = 'ADMIN', 'Admin'

    class EventScope(models.TextChoices):
        MAKER = 'MAKER', 'Maker'
        CODER = 'CODER', 'Coder'
        MANAGER = 'MANAGER', 'Manager'
        CREATIVE = 'CREATIVE', 'Creative'

    class EventType(models.TextChoices):
        HACKATHON       = 'HACKATHON',       'Hackathon'
        WORKSHOP        = 'WORKSHOP',        'Workshop'
        WEBINAR         = 'WEBINAR',         'Webinar'
        SEMINAR         = 'SEMINAR',         'Seminar'
        BOOTCAMP        = 'BOOTCAMP',        'Bootcamp'
        MEETUP          = 'MEETUP',          'Meetup'
        CONFERENCE      = 'CONFERENCE',      'Conference'
        COMPETITION     = 'COMPETITION',     'Competition'
        IDEATHON        = 'IDEATHON',        'Ideathon'
        CULTURAL_EVENT  = 'CULTURAL_EVENT',  'Cultural Event'
        SPORTS_EVENT    = 'SPORTS_EVENT',    'Sports Event'
        COMMUNITY_EVENT = 'COMMUNITY_EVENT', 'Community Event'
        EXPO            = 'EXPO',            'Expo'
        NETWORKING_EVENT= 'NETWORKING_EVENT','Networking Event'
        TECH_TALK       = 'TECH_TALK',       'Tech Talk'
        OTHERS          = 'OTHERS',          'Others'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    title = models.CharField(max_length=200)
    slug = models.CharField(max_length=220, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    cover_image = models.CharField(max_length=512, blank=True, null=True)
    banner_image = models.CharField(max_length=512, blank=True, null=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='category_id', related_name='new_events'
    )

    # Lifecycle
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)

    # Dates
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    registration_url = models.CharField(max_length=500, blank=True, null=True)
    registration_deadline = models.DateTimeField(blank=True, null=True)
    min_karma = models.BigIntegerField(blank=True, null=True)

    # Venue (in-line on the events table)
    venue_type = models.CharField(max_length=20, choices=VenueType.choices, default=VenueType.ONLINE)
    venue_address = models.CharField(max_length=300, blank=True, null=True)
    venue_city = models.CharField(max_length=100, blank=True, null=True)
    venue_maps_url = models.CharField(max_length=500, blank=True, null=True)
    venue_online_link = models.CharField(max_length=500, blank=True, null=True)
    venue_platform = models.CharField(max_length=100, blank=True, null=True)

    # Scope & targeting
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.GLOBAL)
    scope_org = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='scope_org_id', related_name='event_scope_org'
    )
    scope_ig = models.ForeignKey(
        InterestGroup, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='scope_ig_id', related_name='event_scope_ig'
    )
    # campus_ig scope: stored as a plain ID (no dedicated campus_ig table yet)
    scope_ci_id = models.CharField(max_length=36, blank=True, null=True)

    # Organiser
    organiser_type = models.CharField(max_length=20, choices=OrganiserType.choices, default=OrganiserType.ADMIN)
    organiser_ig = models.ForeignKey(
        InterestGroup, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='organiser_ig_id', related_name='event_organiser_ig'
    )
    organiser_org = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='organiser_org_id', related_name='event_organiser_org'
    )
    organiser_ci_id = models.CharField(max_length=36, blank=True, null=True)  # campus_ig reference

    # Event scope (audience type)
    event_scope = models.CharField(
        max_length=20, choices=EventScope.choices
    )

    # Event type
    event_type = models.CharField(
        max_length=20, choices=EventType.choices, default=EventType.OTHERS
    )

    # Flags & counters
    is_featured = models.BooleanField(default=False)
    is_collaboration = models.BooleanField(default=False)
    interest_count = models.PositiveIntegerField(default=0)
    tags = models.JSONField(blank=True, null=True)
    user_limit = models.PositiveIntegerField(default=0)

    # Audit
    created_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='created_by', related_name='new_event_created_by'
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='updated_by', related_name='new_event_updated_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'events'


class EventConnection(models.Model):
    """
    Polymorphic connection table for events.
    Handles: user tickets, co-owners, and all collaborator entity types.

    entity_type values:
        user_ticket      → user registered / expressed ticket interest
        co_owner         → user with full manage access
        collab_ig        → IG as co-host
        collab_campus    → campus as co-host
        collab_campus_ig → campus IG chapter as co-host
        collab_company   → company as co-host
    """

    class EntityType(models.TextChoices):
        USER_TICKET = 'USER_TICKET', 'User_Ticket'
        CO_OWNER = 'CO_OWNER', 'Co-owner'
        COLLAB_IG = 'COLLAB_IG', 'Collaborating_IG'
        COLLAB_CAMPUS = 'COLLAB_CAMPUS', 'Collaborating_Campus'
        COLLAB_CAMPUS_IG = 'COLLAB_CAMPUS_IG', 'Collaborating_Campus_IG'
        COLLAB_COMPANY = 'COLLAB_COMPANY', 'Collaborating_Company'

    COLLABORATOR_TYPES = [
        EntityType.COLLAB_IG,
        EntityType.COLLAB_CAMPUS,
        EntityType.COLLAB_CAMPUS_IG,
        EntityType.COLLAB_COMPANY,
    ]

    class InviteStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'

    class TicketStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACTIVE = 'ACTIVE', 'Active'
        REMOVED = 'REMOVED', 'Removed'
        REJECTED = 'REJECTED', 'Rejected'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE,
        db_column='event_id', related_name='connections'
    )
    entity_type = models.CharField(max_length=25, choices=EntityType.choices)
    # Polymorphic FK: user.id / interest_group.id / organization.id depending on entity_type
    entity_id = models.CharField(max_length=36)

    # --- Used only when entity_type = user_ticket ---
    ticket_status = models.CharField(max_length=20, blank=True, null=True)

    # --- Used only for collab_* types ---
    role_label = models.CharField(max_length=100, blank=True, null=True)
    invite_status = models.CharField(
        max_length=20, choices=InviteStatus.choices, blank=True, null=True
    )
    rejection_reason = models.CharField(max_length=500, blank=True, null=True)
    responded_at = models.DateTimeField(blank=True, null=True)

    # Audit
    created_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='created_by', related_name='event_conn_created_by'
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='updated_by', related_name='event_conn_updated_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'events_connection'
        unique_together = [('event', 'entity_id', 'entity_type')]


class EventInterest(models.Model):
    """One row per user-event "I'm Going" click."""

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE,
        db_column='event_id', related_name='interests'
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        db_column='user_id', related_name='event_interests'
    )
    expressed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'events_interest'
        unique_together = [('event', 'user')]


class EventLog(models.Model):
    """Audit trail of every save on an event."""

    class Action:
        """
        Action-type constants stored inside changed_fields['action'].
        Plain class (not TextChoices) — no DB column required.
        """
        CREATED          = 'EVENT_CREATED'
        UPDATED          = 'EVENT_UPDATED'
        PUBLISHED        = 'EVENT_PUBLISHED'
        CANCELLED        = 'EVENT_CANCELLED'
        FEATURED         = 'EVENT_FEATURED'
        UNFEATURED       = 'EVENT_UNFEATURED'
        APPROVED         = 'EVENT_APPROVED'
        REJECTED         = 'EVENT_REJECTED'
        CO_OWNER_ADDED   = 'CO_OWNER_ADDED'
        CO_OWNER_REMOVED = 'CO_OWNER_REMOVED'
        COLLAB_INVITED   = 'COLLABORATOR_INVITED'
        COLLAB_ACCEPTED  = 'COLLABORATOR_ACCEPTED'
        COLLAB_REJECTED  = 'COLLABORATOR_REJECTED'
        COLLAB_REMOVED   = 'COLLABORATOR_REMOVED'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE,
        db_column='event_id', related_name='logs'
    )
    edited_by = models.ForeignKey(
        User, on_delete=models.RESTRICT,
        db_column='edited_by', related_name='event_logs'
    )
    changed_fields = models.JSONField()  # e.g. ["title", "venue_city", "min_karma"]
    edited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'events_log'

class EventTag(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    title = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'event_tag'


class EventTagLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE,
        db_column='event_id', related_name='tag_links'
    )
    tag = models.ForeignKey(
        EventTag, on_delete=models.CASCADE,
        db_column='tag_id', related_name='event_links'
    )

    class Meta:
        managed = False
        db_table = 'event_tag_link'
        unique_together = [('event', 'tag')]


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
        OFFICE_HOURS          = 'office_hours',           'Office Hours'
        SALT_MANGO_TREE       = 'salt_mango_tree',        'Salt Mango Tree'
        INSPIRATION_STATION   = 'inspiration_station',    'Inspiration Station Radio'
        GRAB_YOUR_SUPERPOWERS = 'grab_your_superpowers',  'Grab Your Superpowers'

    class Zone(models.TextChoices):
        NORTH   = 'NORTH',   'North'
        CENTRAL = 'CENTRAL', 'Central'
        SOUTH   = 'SOUTH',   'South'

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
    time        = models.TimeField(blank=True, null=True)  # required at the serializer level for all content types
    description = models.TextField(blank=True, null=True)
    link        = models.CharField(max_length=500, blank=True, null=True)

    # ── Office Hours specific ─────────────────────────────────────────────────
    performer        = models.CharField(max_length=200, blank=True, null=True)
    designation      = models.CharField(max_length=200, blank=True, null=True)
    interest_groups  = models.JSONField(blank=True, null=True)   # list of ig_media_content_link ids for this record
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


class IgMediaContentLink(models.Model):
    """
    Links a MediaContent record (e.g. an Office Hours session) to an
    InterestGroup. MediaContent.interest_groups stores the ids of these
    link rows rather than IG ids/codes directly.
    """
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    media_content = models.ForeignKey(
        MediaContent, on_delete=models.CASCADE,
        db_column='media_content_id', related_name='ig_links'
    )
    interest_group = models.ForeignKey(
        InterestGroup, on_delete=models.CASCADE,
        db_column='ig_id', related_name='media_content_links'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'ig_media_content_link'
        unique_together = [('media_content', 'interest_group')]
