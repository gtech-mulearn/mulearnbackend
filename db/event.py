import uuid

from django.db import models
from django.conf import settings

from .user import User
from .organization import Organization
from .task import InterestGroup

# fmt: off
# noinspection PyPep8


class Event(models.Model):
    """Core event record — one row per event."""

    class EventType(models.TextChoices):
        WORKSHOP        = 'workshop',         'Workshop'
        WEBINAR         = 'webinar',          'Webinar'
        HACKATHON       = 'hackathon',        'Hackathon'
        MEETUP          = 'meetup',           'Meetup'
        COMPETITION     = 'competition',      'Competition'
        SOCIAL_GATHERING = 'social_gathering', 'Social Gathering'
        OTHER           = 'other',            'Other'

    class Status(models.TextChoices):
        DRAFT                    = 'draft',                    'Draft'
        PENDING_CAMPUS_APPROVAL  = 'pending_campus_approval',  'Pending Campus Approval'
        PENDING_APPROVAL         = 'pending_approval',         'Pending Approval'
        PENDING_MENTOR_APPROVAL  = 'pending_mentor_approval',  'Pending Mentor Approval'
        PUBLISHED                = 'published',                'Published'
        ONGOING                  = 'ongoing',                  'Ongoing'
        COMPLETED                = 'completed',                'Completed'
        CANCELLED                = 'cancelled',                'Cancelled'

    id              = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    title           = models.CharField(max_length=200)
    slug            = models.CharField(max_length=220, unique=True)
    description     = models.TextField()
    cover_image     = models.CharField(max_length=500, blank=True, null=True)
    banner_image    = models.CharField(max_length=500, blank=True, null=True)
    event_type      = models.CharField(max_length=20, choices=EventType.choices, default=EventType.OTHER)
    status          = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)

    start_datetime        = models.DateTimeField()
    end_datetime          = models.DateTimeField()

    registration_url      = models.CharField(max_length=500, blank=True, null=True)
    registration_deadline = models.DateTimeField(blank=True, null=True)

    min_karma             = models.BigIntegerField(blank=True, null=True)

    is_collaboration      = models.BooleanField(default=False)
    is_featured           = models.BooleanField(default=False)
    interest_count        = models.IntegerField(default=0)

    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
                                   db_column="created_by", related_name="event_v2_created_by")
    created_at = models.DateTimeField()
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
                                   db_column="updated_by", related_name="event_v2_updated_by")
    updated_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True,
                                   db_column="deleted_by", related_name="event_v2_deleted_by")

    class Meta:
        managed  = False
        db_table = "event"


class EventTag(models.Model):
    """Normalised tag dictionary."""

    id         = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    name       = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField()

    class Meta:
        managed  = False
        db_table = "event_tag"


class EventTagLink(models.Model):
    """Event ↔ Tag M2M join table."""

    id         = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    event      = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="tag_links")
    tag        = models.ForeignKey(EventTag, on_delete=models.CASCADE, related_name="event_links")
    created_at = models.DateTimeField()

    class Meta:
        managed       = False
        db_table      = "event_tag_link"
        unique_together = [("event", "tag")]


class EventVenue(models.Model):
    """Venue details — 1-to-1 with Event."""

    class VenueType(models.TextChoices):
        PHYSICAL = 'physical', 'Physical'
        ONLINE   = 'online',   'Online'
        HYBRID   = 'hybrid',   'Hybrid'

    id          = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    event       = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="venue")
    venue_type  = models.CharField(max_length=10, choices=VenueType.choices)

    # Physical / hybrid
    address     = models.CharField(max_length=300, blank=True, null=True)
    city        = models.CharField(max_length=100, blank=True, null=True)
    maps_url    = models.CharField(max_length=500, blank=True, null=True)

    # Online / hybrid
    online_link = models.CharField(max_length=500, blank=True, null=True)
    platform    = models.CharField(max_length=100, blank=True, null=True)

    created_at  = models.DateTimeField()
    updated_at  = models.DateTimeField()

    class Meta:
        managed  = False
        db_table = "event_venue"


class EventScope(models.Model):
    """Scope / visibility targeting — 1-to-1 with Event."""

    class ScopeType(models.TextChoices):
        GLOBAL    = 'global',    'Global'
        CAMPUS    = 'campus',    'Campus'
        IG        = 'ig',        'IG'
        CAMPUS_IG = 'campus_ig', 'Campus IG'

    id              = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    event           = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="scope")
    scope           = models.CharField(max_length=10, choices=ScopeType.choices, default=ScopeType.GLOBAL)

    target_org_id   = models.ForeignKey(Organization, on_delete=models.SET_NULL, blank=True, null=True,
                                        db_column="target_org_id", related_name="event_scope_campus")
    target_ig_id    = models.ForeignKey(InterestGroup, on_delete=models.SET_NULL, blank=True, null=True,
                                        db_column="target_ig_id", related_name="event_scope_ig")
    target_ci_org_id = models.ForeignKey(Organization, on_delete=models.SET_NULL, blank=True, null=True,
                                         db_column="target_ci_org_id", related_name="event_scope_ci_campus")
    target_ci_ig_id  = models.ForeignKey(InterestGroup, on_delete=models.SET_NULL, blank=True, null=True,
                                         db_column="target_ci_ig_id", related_name="event_scope_ci_ig")

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed  = False
        db_table = "event_scope"


class EventOrganiser(models.Model):
    """Who owns the event — 1-to-1 with Event."""

    class OrganiserType(models.TextChoices):
        GLOBAL_IG = 'global_ig',  'Global IG'
        CAMPUS_IG = 'campus_ig',  'Campus IG'
        CAMPUS    = 'campus',     'Campus'
        COMPANY   = 'company',    'Company'
        ADMIN     = 'admin',      'Admin'

    id             = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    event          = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="organiser")
    organiser_type = models.CharField(max_length=10, choices=OrganiserType.choices)

    ig_id     = models.ForeignKey(InterestGroup, on_delete=models.SET_NULL, blank=True, null=True,
                                  db_column="ig_id", related_name="event_organiser_ig")
    org_id    = models.ForeignKey(Organization, on_delete=models.SET_NULL, blank=True, null=True,
                                  db_column="org_id", related_name="event_organiser_org")
    ci_org_id = models.ForeignKey(Organization, on_delete=models.SET_NULL, blank=True, null=True,
                                  db_column="ci_org_id", related_name="event_organiser_ci_org")
    ci_ig_id  = models.ForeignKey(InterestGroup, on_delete=models.SET_NULL, blank=True, null=True,
                                  db_column="ci_ig_id", related_name="event_organiser_ci_ig")

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed  = False
        db_table = "event_organiser"


class EventCollaborator(models.Model):
    """Co-host invites — many per event."""

    class CollaboratorType(models.TextChoices):
        IG        = 'ig',        'IG'
        CAMPUS    = 'campus',    'Campus'
        CAMPUS_IG = 'campus_ig', 'Campus IG'
        COMPANY   = 'company',   'Company'

    class InviteStatus(models.TextChoices):
        PENDING  = 'pending',  'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'

    id                = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    event             = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="collaborators")
    collaborator_type = models.CharField(max_length=10, choices=CollaboratorType.choices)

    ig_id     = models.ForeignKey(InterestGroup, on_delete=models.CASCADE, blank=True, null=True,
                                  db_column="ig_id", related_name="event_collaborator_ig")
    org_id    = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True,
                                  db_column="org_id", related_name="event_collaborator_org")
    ci_org_id = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True,
                                  db_column="ci_org_id", related_name="event_collaborator_ci_org")
    ci_ig_id  = models.ForeignKey(InterestGroup, on_delete=models.CASCADE, blank=True, null=True,
                                  db_column="ci_ig_id", related_name="event_collaborator_ci_ig")

    role_label       = models.CharField(max_length=100, blank=True, null=True)
    invite_status    = models.CharField(max_length=10, choices=InviteStatus.choices, default=InviteStatus.PENDING)
    rejection_reason = models.CharField(max_length=500, blank=True, null=True)
    invited_at       = models.DateTimeField()
    responded_at     = models.DateTimeField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
                                   db_column="created_by", related_name="event_collaborator_created_by")
    created_at = models.DateTimeField()

    class Meta:
        managed  = False
        db_table = "event_collaborator"


class EventInterest(models.Model):
    """"I'm Going" signals — one per user per event."""

    id           = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    event        = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="interests")
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="event_interests")
    expressed_at = models.DateTimeField()

    class Meta:
        managed       = False
        db_table      = "event_interest"
        unique_together = [("event", "user")]


class EventEditLog(models.Model):
    """Audit trail for the manage view."""

    id             = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    event          = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="edit_logs")
    edited_by      = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
                                       db_column="edited_by", related_name="event_edit_log_editor")
    changed_fields = models.JSONField()
    edited_at      = models.DateTimeField()

    class Meta:
        managed  = False
        db_table = "event_edit_log"


class EventCoOwner(models.Model):
    """Users with full owner-level authority on an event."""

    class CoOwnerRole(models.TextChoices):
        CO_OWNER = 'co_owner', 'Co-Owner'
        ADMIN    = 'admin',    'Admin'

    id       = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    event    = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="co_owners")
    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name="event_co_ownerships")
    role     = models.CharField(max_length=10, choices=CoOwnerRole.choices, default=CoOwnerRole.CO_OWNER)
    added_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
                                 db_column="added_by", related_name="event_co_owner_added_by")
    added_at = models.DateTimeField()

    class Meta:
        managed       = False
        db_table      = "event_co_owner"
        unique_together = [("event", "user")]
