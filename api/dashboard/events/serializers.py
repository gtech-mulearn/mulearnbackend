"""
Shared serializers for the Events system.
All view modules import from this file.
"""
import uuid

from django.utils.text import slugify
from rest_framework import serializers

from db.events import Event, EventConnection, EventInterest, EventLog
from db.task import InterestGroup, TaskList
from db.organization import Organization
from db.user import User
from utils.utils import DateTimeUtils

from .event_image_utils import resolve_event_image_url


# ─────────────────────────────────────────────────────────────
# MINIMAL / NESTED SHAPES
# ─────────────────────────────────────────────────────────────

class MinimalUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'full_name', 'muid', 'profile_pic']


class MinimalIGSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterestGroup
        fields = ['id', 'name', 'icon']


class MinimalCampusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'title', 'org_type']


class MinimalCampusIGSerializer(serializers.Serializer):
    """Represents a campus-IG chapter as (org_id, ig_id) pair."""
    org_id = serializers.CharField()
    ig_id = serializers.CharField()
    org_title = serializers.CharField()
    ig_name = serializers.CharField()


# ─────────────────────────────────────────────────────────────
# ORGANISER INFO
# ─────────────────────────────────────────────────────────────

class OrganizerInfoSerializer(serializers.Serializer):
    """Reads organiser fields off the Event model directly."""
    type = serializers.CharField(source='organiser_type')
    ig = serializers.SerializerMethodField()
    campus = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    campus_ig_id = serializers.CharField(source='organiser_ci_id', allow_null=True)

    def get_ig(self, obj):
        if obj.organiser_type in (Event.OrganiserType.GLOBAL_IG, Event.OrganiserType.CAMPUS_IG) and obj.organiser_ig:
            return MinimalIGSerializer(obj.organiser_ig).data
        return None

    def get_campus(self, obj):
        if obj.organiser_type == Event.OrganiserType.CAMPUS and obj.organiser_org:
            return MinimalCampusSerializer(obj.organiser_org).data
        return None

    def get_company(self, obj):
        if obj.organiser_type == Event.OrganiserType.COMPANY and obj.organiser_org:
            return MinimalCampusSerializer(obj.organiser_org).data
        return None


# ─────────────────────────────────────────────────────────────
# VENUE
# ─────────────────────────────────────────────────────────────

class EventVenueSerializer(serializers.Serializer):
    """Flattens venue_* fields from the Event model."""
    type = serializers.CharField(source='venue_type')
    address = serializers.CharField(source='venue_address', allow_null=True)
    city = serializers.CharField(source='venue_city', allow_null=True)
    maps_url = serializers.CharField(source='venue_maps_url', allow_null=True)
    online_link = serializers.CharField(source='venue_online_link', allow_null=True)
    platform = serializers.CharField(source='venue_platform', allow_null=True)


# ─────────────────────────────────────────────────────────────
# COLLABORATORS
# ─────────────────────────────────────────────────────────────

class EventCollaboratorSerializer(serializers.ModelSerializer):
    entity_detail = serializers.SerializerMethodField()

    class Meta:
        model = EventConnection
        fields = [
            'id', 'entity_type', 'entity_id', 'entity_detail',
            'role_label', 'invite_status', 'rejection_reason',
            'responded_at', 'created_at',
        ]

    def get_entity_detail(self, obj):
        try:
            if obj.entity_type == EventConnection.EntityType.COLLAB_IG:
                ig = InterestGroup.objects.filter(id=obj.entity_id).first()
                return MinimalIGSerializer(ig).data if ig else None
            elif obj.entity_type in (
                EventConnection.EntityType.COLLAB_CAMPUS,
                EventConnection.EntityType.COLLAB_COMPANY,
            ):
                org = Organization.objects.filter(id=obj.entity_id).first()
                return MinimalCampusSerializer(org).data if org else None
            elif obj.entity_type == EventConnection.EntityType.COLLAB_CAMPUS_IG:
                return {'campus_ig_id': obj.entity_id}
            elif obj.entity_type == EventConnection.EntityType.COLLAB_PARTNER:
                from db.partner import UserPartner
                partner = UserPartner.objects.filter(id=obj.entity_id).first()
                if partner:
                    return {
                        'id': partner.id,
                        'name': partner.name,
                        'slug': partner.slug,
                        'logo': partner.logo,
                    }
        except Exception:
            return None
        return None


class MyEventInviteSerializer(EventCollaboratorSerializer):
    event_id = serializers.CharField(source='event.id', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)
    event_start_datetime = serializers.DateTimeField(source='event.start_datetime', read_only=True)
    event_cover_image = serializers.SerializerMethodField()

    class Meta(EventCollaboratorSerializer.Meta):
        fields = EventCollaboratorSerializer.Meta.fields + [
            'event_id', 'event_title', 'event_start_datetime', 'event_cover_image'
        ]

    def get_event_cover_image(self, obj):
        ev = getattr(obj, 'event', None)
        if not ev:
            return None
        return resolve_event_image_url(ev.cover_image, self.context.get('request'))



# ─────────────────────────────────────────────────────────────
# CO-OWNERS
# ─────────────────────────────────────────────────────────────

class EventCoOwnerSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    added_by = serializers.SerializerMethodField()
    added_at = serializers.DateTimeField(source='created_at')

    class Meta:
        model = EventConnection
        fields = ['id', 'entity_id', 'user', 'added_by', 'added_at']

    def get_user(self, obj):
        user = User.objects.filter(id=obj.entity_id).first()
        return MinimalUserSerializer(user).data if user else None

    def get_added_by(self, obj):
        return MinimalUserSerializer(obj.created_by).data


# ─────────────────────────────────────────────────────────────
# LINKED TASKS
# ─────────────────────────────────────────────────────────────

class LinkedTaskSerializer(serializers.ModelSerializer):
    ig = MinimalIGSerializer(read_only=True)

    class Meta:
        model = TaskList
        fields = [
            'id', 'title', 'description', 'hashtag',
            'karma', 'bonus_time', 'bonus_karma', 'active', 'ig',
        ]


# ─────────────────────────────────────────────────────────────
# EVENT LIST ITEM  (lean — for paginated feeds)
# ─────────────────────────────────────────────────────────────

class EventListItemSerializer(serializers.ModelSerializer):
    organizer = OrganizerInfoSerializer(source='*')
    venue = EventVenueSerializer(source='*')
    viewer_interest_status = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', allow_null=True, read_only=True)
    category_id   = serializers.CharField(source='category.id',   allow_null=True, read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'slug', 'cover_image',
            'status', 'scope', 'start_datetime', 'end_datetime',
            'venue', 'organizer', 'is_featured', 'is_collaboration',
            'interest_count', 'min_karma', 'tags', 'user_limit',
            'category_id', 'category_name', 'viewer_interest_status',
        ]

    def get_cover_image(self, obj):
        return resolve_event_image_url(obj.cover_image, self.context.get('request'))

    def get_viewer_interest_status(self, obj):
        user_id = self.context.get('user_id')
        if not user_id:
            return None
        # Use queryset annotation when available (avoids N+1 per list item);
        # fall back to a direct query if the annotation is not present (e.g. detail view).
        if hasattr(obj, 'viewer_interested'):
            return 'interested' if obj.viewer_interested else 'none'
        exists = EventInterest.objects.filter(event=obj, user_id=user_id).exists()
        return 'interested' if exists else 'none'


class EventCalendarItemSerializer(serializers.ModelSerializer):
    start = serializers.DateTimeField(source='start_datetime', read_only=True)
    end = serializers.DateTimeField(source='end_datetime', read_only=True)
    category_name = serializers.CharField(source='category.name', allow_null=True, read_only=True)
    organiser_name = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'slug', 'status', 'start', 'end',
            'venue_type', 'organiser_name', 'category_name', 'is_featured',
        ]

    def get_organiser_name(self, obj):
        if obj.organiser_type in [Event.OrganiserType.CAMPUS, Event.OrganiserType.COMPANY]:
            return obj.organiser_org.title if obj.organiser_org else "muLearn"
        elif obj.organiser_type in [Event.OrganiserType.GLOBAL_IG, Event.OrganiserType.CAMPUS_IG]:
            return obj.organiser_ig.name if obj.organiser_ig else "muLearn"
        return "muLearn"


# ─────────────────────────────────────────────────────────────
# EVENT DETAIL  (full — for detail page)
# ─────────────────────────────────────────────────────────────

class EventDetailSerializer(serializers.ModelSerializer):
    organizer = OrganizerInfoSerializer(source='*')
    venue = EventVenueSerializer(source='*')
    collaborators = serializers.SerializerMethodField()
    co_owners = serializers.SerializerMethodField()
    linked_tasks = serializers.SerializerMethodField()
    created_by = MinimalUserSerializer(read_only=True)
    updated_by = MinimalUserSerializer(read_only=True)
    viewer_interest_status = serializers.SerializerMethodField()
    viewer_can_access_registration = serializers.SerializerMethodField()
    viewer_access_blocked_reason = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()
    banner_image = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', allow_null=True, read_only=True)
    category_id   = serializers.CharField(source='category.id',   allow_null=True, read_only=True)
    scope_org = MinimalCampusSerializer(read_only=True, allow_null=True)
    scope_ig = MinimalIGSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'slug', 'description',
            'cover_image', 'banner_image', 'category_id', 'category_name',
            'status', 'scope', 'scope_org', 'scope_ig', 'scope_ci_id',
            'organizer', 'venue',
            'start_datetime', 'end_datetime',
            'registration_url', 'registration_deadline', 'min_karma',
            'is_featured', 'is_collaboration', 'interest_count',
            'tags', 'user_limit',
            'linked_tasks', 'co_owners', 'collaborators',
            'viewer_interest_status',
            'viewer_can_access_registration',
            'viewer_access_blocked_reason',
            'created_by', 'updated_by', 'created_at', 'updated_at',
        ]

    def get_cover_image(self, obj):
        return resolve_event_image_url(obj.cover_image, self.context.get('request'))

    def get_banner_image(self, obj):
        return resolve_event_image_url(obj.banner_image, self.context.get('request'))

    def get_collaborators(self, obj):
        is_manage_view = self.context.get('is_manage_view', False)
        qs = obj.connections.filter(
            entity_type__in=EventConnection.COLLABORATOR_TYPES
        )
        if not is_manage_view:
            # Public view: only accepted collaborators
            qs = qs.filter(invite_status=EventConnection.InviteStatus.ACCEPTED)
        return EventCollaboratorSerializer(qs, many=True).data

    def get_co_owners(self, obj):
        qs = obj.connections.filter(entity_type=EventConnection.EntityType.CO_OWNER)
        return EventCoOwnerSerializer(qs, many=True).data

    def get_linked_tasks(self, obj):
        # Use event_fk_id (raw UUID) to avoid Django's FK type-check
        # which rejects a new `Event` object where old `Events` is expected.
        tasks = TaskList.objects.filter(event_fk_id=obj.id)
        return LinkedTaskSerializer(tasks, many=True).data

    def _get_viewer_info(self, obj):
        """Returns (user_id, viewer_karma). Cached per serializer call."""
        if hasattr(self, '_viewer_info_cache'):
            return self._viewer_info_cache
        user_id = self.context.get('user_id')
        if not user_id:
            self._viewer_info_cache = (None, None)
            return self._viewer_info_cache
        try:
            from db.task import Wallet
            wallet = Wallet.objects.filter(user_id=user_id).first()
            karma = wallet.karma if wallet else 0
        except Exception:
            karma = 0
        self._viewer_info_cache = (user_id, karma)
        return self._viewer_info_cache

    def get_viewer_interest_status(self, obj):
        user_id, _ = self._get_viewer_info(obj)
        if not user_id:
            return None
        if hasattr(obj, 'viewer_interested'):
            return 'interested' if obj.viewer_interested else 'none'
        exists = EventInterest.objects.filter(event=obj, user_id=user_id).exists()
        return 'interested' if exists else 'none'

    def get_viewer_can_access_registration(self, obj):
        user_id, karma = self._get_viewer_info(obj)
        if not user_id:
            # Unauthenticated: only global events with no karma gate
            return obj.scope == Event.Scope.GLOBAL and not obj.min_karma
        if obj.status in (Event.Status.CANCELLED, Event.Status.COMPLETED, Event.Status.DRAFT):
            return False
        if obj.min_karma and karma < obj.min_karma:
            return False
        return True

    def get_viewer_access_blocked_reason(self, obj):
        user_id, karma = self._get_viewer_info(obj)
        if obj.status == Event.Status.CANCELLED:
            return 'This event has been cancelled.'
        if obj.status == Event.Status.COMPLETED:
            return 'This event has already completed.'
        if obj.status == Event.Status.DRAFT:
            return 'This event is not yet published.'
        if obj.min_karma and user_id and karma < obj.min_karma:
            return f'Requires {obj.min_karma:,} karma. You have {karma:,}.'
        return None


# ─────────────────────────────────────────────────────────────
# EVENT WRITE  (create / update input)
# ─────────────────────────────────────────────────────────────

class EventWriteSerializer(serializers.ModelSerializer):
    """Input serializer for POST /manage/ and PUT/PATCH /manage/<id>/."""

    class Meta:
        model = Event
        fields = [
            'title', 'description', 'cover_image', 'banner_image', 'category',
            'start_datetime', 'end_datetime',
            'registration_url', 'registration_deadline', 'min_karma',
            'venue_type', 'venue_address', 'venue_city',
            'venue_maps_url', 'venue_online_link', 'venue_platform',
            'scope', 'scope_org', 'scope_ig', 'scope_ci_id',
            'organiser_type', 'organiser_ig', 'organiser_org', 'organiser_ci_id',
            'is_collaboration', 'is_featured', 'tags', 'user_limit',
        ]
        extra_kwargs = {
            'description': {'required': False, 'allow_null': True},
            'cover_image': {'required': False, 'allow_null': True},
            'banner_image': {'required': False, 'allow_null': True},
            'category': {'required': False, 'allow_null': True},
            'registration_url': {'required': False, 'allow_null': True},
            'registration_deadline': {'required': False, 'allow_null': True},
            'min_karma': {'required': False, 'allow_null': True},
            'venue_address': {'required': False, 'allow_null': True},
            'venue_city': {'required': False, 'allow_null': True},
            'venue_maps_url': {'required': False, 'allow_null': True},
            'venue_online_link': {'required': False, 'allow_null': True},
            'venue_platform': {'required': False, 'allow_null': True},
            'scope_org': {'required': False, 'allow_null': True},
            'scope_ig': {'required': False, 'allow_null': True},
            'scope_ci_id': {'required': False, 'allow_null': True},
            'organiser_ig': {'required': False, 'allow_null': True},
            'organiser_org': {'required': False, 'allow_null': True},
            'organiser_ci_id': {'required': False, 'allow_null': True},
            'is_collaboration': {'required': False},
            'is_featured': {'required': False},
            'tags': {'required': False, 'allow_null': True},
            'user_limit': {'required': False},
        }

    def validate_category(self, value):
        """Ensure the provided Category belongs to the event entity type."""
        if value is None:
            return value
        from db.task import Category as CategoryModel
        # Re-fetch to confirm this category exists and is scoped to events
        cat = CategoryModel.objects.filter(
            id=value.id,
            entity_type=CategoryModel.EntityType.EVENT,
        ).first()
        if not cat:
            raise serializers.ValidationError(
                'Invalid category: must be an event category. '
                'Use GET /events/meta/categories/ to list valid options.'
            )
        return value

    def validate(self, attrs):
        start = attrs.get('start_datetime')
        end = attrs.get('end_datetime')
        
        # In a partial update (PATCH), if only one is provided, compare against the existing instance
        if self.instance:
            if not start:
                start = self.instance.start_datetime
            if not end:
                end = self.instance.end_datetime

        if start and end and end <= start:
            raise serializers.ValidationError({'end_datetime': 'Must be after start_datetime.'})
            
        # Enforce Campus Scope Ownership Validation
        organiser_type = attrs.get('organiser_type', self.instance.organiser_type if self.instance else None)
        scope = attrs.get('scope', self.instance.scope if self.instance else None)
        
        if organiser_type == Event.OrganiserType.CAMPUS and scope == Event.Scope.CAMPUS:
            organiser_org = attrs.get('organiser_org', self.instance.organiser_org if self.instance else None)
            scope_org = attrs.get('scope_org', self.instance.scope_org if self.instance else None)
            
            if scope_org != organiser_org:
                raise serializers.ValidationError(
                    {'scope_org': "Campus scoped events can only target the organiser's own campus."}
                )

        return attrs

    def _generate_unique_slug(self, title):
        base = slugify(title)
        slug = base
        counter = 1
        while Event.objects.filter(slug=slug).exists():
            slug = f'{base}-{counter}'
            counter += 1
        return slug

    def create(self, validated_data):
        user_id = self.context['user_id']
        validated_data['id'] = str(uuid.uuid4())
        validated_data['slug'] = self._generate_unique_slug(validated_data['title'])
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id
        return Event.objects.create(**validated_data)

    def update(self, instance, validated_data):
        from .event_logger import build_diff, log_event_action

        user_id = self.context['user_id']

        # Capture diff BEFORE applying changes so we have old values
        changes = build_diff(instance, validated_data)

        if 'title' in validated_data and validated_data['title'] != instance.title:
            validated_data['slug'] = self._generate_unique_slug(validated_data['title'])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.updated_by_id = user_id
        instance.save()

        # Write structured audit log (only if something actually changed)
        if changes:
            log_event_action(
                event=instance,
                user_id=user_id,
                action=EventLog.Action.UPDATED,
                changes=changes,
            )
        return instance


# ─────────────────────────────────────────────────────────────
# EDIT HISTORY (manage detail view)
# ─────────────────────────────────────────────────────────────

class EventLogSerializer(serializers.ModelSerializer):
    edited_by = MinimalUserSerializer(read_only=True)
    action    = serializers.SerializerMethodField()
    summary   = serializers.SerializerMethodField()
    changes   = serializers.SerializerMethodField()
    details   = serializers.SerializerMethodField()

    class Meta:
        model = EventLog
        fields = ['id', 'action', 'edited_by', 'summary', 'changes', 'details', 'edited_at']

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _cf(self, obj):
        """Always return changed_fields as a dict (handles legacy list rows)."""
        cf = obj.changed_fields
        return cf if isinstance(cf, dict) else {}

    def get_action(self, obj):
        return self._cf(obj).get('action', 'event_updated')

    def get_changes(self, obj):
        return self._cf(obj).get('changes', {})

    def get_details(self, obj):
        return self._cf(obj).get('details', None)

    def get_summary(self, obj):
        action  = self.get_action(obj)
        changes = self.get_changes(obj)
        details = self.get_details(obj) or {}

        ACTION_SUMMARIES = {
            'event_created':         lambda c, d: 'Event created',
            'event_updated':         lambda c, d: f"Updated: {', '.join(c.keys())}" if c else 'Event updated',
            'event_published':       lambda c, d: f"Event submitted for approval → {d.get('new_status', '')}".rstrip(' →'),
            'event_cancelled':       lambda c, d: 'Event cancelled',
            'event_approved':        lambda c, d: f"Event approved → {c.get('Status', {}).get('to', '')}".rstrip(' →'),
            'event_rejected':        lambda c, d: f"Event rejected — {d.get('reason', 'no reason given')}",
            'event_featured':        lambda c, d: 'Event marked as featured',
            'event_unfeatured':      lambda c, d: 'Event removed from featured',
            'co_owner_added':        lambda c, d: f"Co-owner added: {d.get('name', '')}".rstrip(': '),
            'co_owner_removed':      lambda c, d: f"Co-owner removed: {d.get('name', '')}".rstrip(': '),
            'collaborator_invited':  lambda c, d: f"{d.get('entity_type', 'Collaborator')} invited: {d.get('name', '')}".rstrip(': '),
            'collaborator_accepted': lambda c, d: f"{d.get('entity_type', 'Collaborator')} accepted the invite: {d.get('name', '')}".rstrip(': '),
            'collaborator_rejected': lambda c, d: f"{d.get('entity_type', 'Collaborator')} rejected the invite: {d.get('name', '')} — {d.get('reason', '')}".rstrip(' —: '),
            'collaborator_removed':  lambda c, d: f"{d.get('entity_type', 'Collaborator')} removed: {d.get('name', '')}".rstrip(': '),
        }
        fn = ACTION_SUMMARIES.get(action)
        return fn(changes, details) if fn else action.replace('_', ' ').title()


# ─────────────────────────────────────────────────────────────
# HELPERS (used inside views — not serializers)
# ─────────────────────────────────────────────────────────────

def get_live_events():
    """Base queryset: non-deleted events."""
    return Event.objects.filter(deleted_at__isnull=True)


def can_manage_event(user_id, event):
    """True if user is creator OR co-owner of this event."""
    if event.created_by_id == user_id:
        return True
    return EventConnection.objects.filter(
        event=event,
        entity_type=EventConnection.EntityType.CO_OWNER,
        entity_id=user_id,
    ).exists()
