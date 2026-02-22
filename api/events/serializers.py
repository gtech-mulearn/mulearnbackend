"""
Serializers for the Events system.

Covers: list (lean card), detail (rich full), write (create/update),
and supporting nested serializers for venue, scope, organiser, etc.
"""

import uuid

from django.utils.text import slugify
from rest_framework import serializers

from db.event import (
    Event, EventCoOwner, EventCollaborator, EventEditLog,
    EventInterest, EventOrganiser, EventScope, EventTag,
    EventTagLink, EventVenue,
)
from db.organization import Organization
from db.task import InterestGroup
from db.user import User
from utils.utils import DateTimeUtils


# ──────────────────────────────────────────────────
# READ — Supporting Serializers
# ──────────────────────────────────────────────────

class EventTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventTag
        fields = ["id", "name"]


class EventVenueReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventVenue
        fields = [
            "venue_type", "address", "city", "maps_url",
            "online_link", "platform",
        ]


class EventScopeReadSerializer(serializers.ModelSerializer):
    target_org_name = serializers.CharField(source="target_org_id.title", default=None)
    target_ig_name = serializers.CharField(source="target_ig_id.name", default=None)

    class Meta:
        model = EventScope
        fields = [
            "scope", "target_org_id", "target_ig_id",
            "target_ci_org_id", "target_ci_ig_id",
            "target_org_name", "target_ig_name",
        ]


class EventOrganiserReadSerializer(serializers.ModelSerializer):
    ig_name = serializers.CharField(source="ig_id.name", default=None)
    org_name = serializers.CharField(source="org_id.title", default=None)
    ci_org_name = serializers.CharField(source="ci_org_id.title", default=None)
    ci_ig_name = serializers.CharField(source="ci_ig_id.name", default=None)

    class Meta:
        model = EventOrganiser
        fields = [
            "organiser_type", "ig_id", "org_id",
            "ci_org_id", "ci_ig_id",
            "ig_name", "org_name", "ci_org_name", "ci_ig_name",
        ]


class EventCollaboratorReadSerializer(serializers.ModelSerializer):
    ig_name = serializers.CharField(source="ig_id.name", default=None)
    org_name = serializers.CharField(source="org_id.title", default=None)
    ci_org_name = serializers.CharField(source="ci_org_id.title", default=None)
    ci_ig_name = serializers.CharField(source="ci_ig_id.name", default=None)

    class Meta:
        model = EventCollaborator
        fields = [
            "id", "collaborator_type",
            "ig_id", "org_id", "ci_org_id", "ci_ig_id",
            "ig_name", "org_name", "ci_org_name", "ci_ig_name",
            "role_label", "invite_status", "rejection_reason",
            "invited_at", "responded_at",
        ]


class EventCoOwnerReadSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = EventCoOwner
        fields = ["id", "user_id", "full_name", "role", "added_at"]


class EventEditLogSerializer(serializers.ModelSerializer):
    edited_by_name = serializers.CharField(source="edited_by.full_name", read_only=True)

    class Meta:
        model = EventEditLog
        fields = ["id", "edited_by", "edited_by_name", "changed_fields", "edited_at"]


# ──────────────────────────────────────────────────
# READ — List (lean) & Detail (rich)
# ──────────────────────────────────────────────────

class EventListSerializer(serializers.ModelSerializer):
    """Lean card data for feeds (EventListItem shape)."""

    tags = serializers.SerializerMethodField()
    venue_type = serializers.SerializerMethodField()
    organiser_type = serializers.SerializerMethodField()
    organiser_name = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id", "title", "slug", "cover_image", "event_type",
            "status", "start_datetime", "end_datetime",
            "is_featured", "interest_count", "venue_type",
            "organiser_type", "organiser_name", "tags",
        ]

    def get_tags(self, obj):
        return list(
            EventTagLink.objects.filter(event=obj)
            .values_list("tag__name", flat=True)
        )

    def get_venue_type(self, obj):
        venue = EventVenue.objects.filter(event=obj).first()
        return venue.venue_type if venue else None

    def get_organiser_type(self, obj):
        org = EventOrganiser.objects.filter(event=obj).first()
        return org.organiser_type if org else None

    def get_organiser_name(self, obj):
        org = EventOrganiser.objects.filter(event=obj).select_related(
            "ig_id", "org_id", "ci_org_id", "ci_ig_id"
        ).first()
        if not org:
            return None
        if org.organiser_type == 'global_ig' and org.ig_id:
            return org.ig_id.name
        if org.organiser_type in ('campus', 'company') and org.org_id:
            return org.org_id.title
        if org.organiser_type == 'campus_ig':
            parts = []
            if org.ci_org_id:
                parts.append(org.ci_org_id.title)
            if org.ci_ig_id:
                parts.append(org.ci_ig_id.name)
            return " × ".join(parts) if parts else None
        if org.organiser_type == 'admin':
            return "μLearn"
        return None


class EventDetailSerializer(serializers.ModelSerializer):
    """Rich full object for detail / manage pages (EventDetail shape)."""

    venue = EventVenueReadSerializer(read_only=True)
    scope = EventScopeReadSerializer(read_only=True)
    organiser = EventOrganiserReadSerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    collaborators = serializers.SerializerMethodField()
    co_owners = EventCoOwnerReadSerializer(source="co_owners.all", many=True, read_only=True)
    edit_history = EventEditLogSerializer(source="edit_logs.all", many=True, read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    viewer_interest = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id", "title", "slug", "description",
            "cover_image", "banner_image", "event_type",
            "status", "start_datetime", "end_datetime",
            "registration_url", "registration_deadline",
            "min_karma", "is_collaboration", "is_featured",
            "interest_count",
            "venue", "scope", "organiser", "tags",
            "collaborators", "co_owners", "edit_history",
            "created_by", "created_by_name", "created_at",
            "updated_at", "viewer_interest",
        ]

    def get_tags(self, obj):
        return list(
            EventTagLink.objects.filter(event=obj)
            .values_list("tag__name", flat=True)
        )

    def get_collaborators(self, obj):
        qs = EventCollaborator.objects.filter(event=obj).select_related(
            "ig_id", "org_id", "ci_org_id", "ci_ig_id"
        )
        return EventCollaboratorReadSerializer(qs, many=True).data

    def get_viewer_interest(self, obj):
        user_id = self.context.get("user_id")
        if not user_id:
            return None
        interest = EventInterest.objects.filter(event=obj, user_id=user_id).first()
        if interest:
            return "going"
        return None


# ──────────────────────────────────────────────────
# WRITE — Venue, Scope, Organiser (nested helpers)
# ──────────────────────────────────────────────────

class EventVenueWriteSerializer(serializers.Serializer):
    venue_type  = serializers.ChoiceField(choices=EventVenue.VenueType.choices)
    address     = serializers.CharField(max_length=300, required=False, allow_null=True, allow_blank=True)
    city        = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    maps_url    = serializers.CharField(max_length=500, required=False, allow_null=True, allow_blank=True)
    online_link = serializers.CharField(max_length=500, required=False, allow_null=True, allow_blank=True)
    platform    = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)


class EventScopeWriteSerializer(serializers.Serializer):
    scope           = serializers.ChoiceField(choices=EventScope.ScopeType.choices)
    target_org_id   = serializers.CharField(max_length=36, required=False, allow_null=True)
    target_ig_id    = serializers.CharField(max_length=36, required=False, allow_null=True)
    target_ci_org_id = serializers.CharField(max_length=36, required=False, allow_null=True)
    target_ci_ig_id  = serializers.CharField(max_length=36, required=False, allow_null=True)


class EventOrganiserWriteSerializer(serializers.Serializer):
    organiser_type = serializers.ChoiceField(choices=EventOrganiser.OrganiserType.choices)
    ig_id          = serializers.CharField(max_length=36, required=False, allow_null=True)
    org_id         = serializers.CharField(max_length=36, required=False, allow_null=True)
    ci_org_id      = serializers.CharField(max_length=36, required=False, allow_null=True)
    ci_ig_id       = serializers.CharField(max_length=36, required=False, allow_null=True)


# ──────────────────────────────────────────────────
# WRITE — Main Event Create / Update
# ──────────────────────────────────────────────────

class EventWriteSerializer(serializers.Serializer):
    """Handles both create and update for events (EventWriteBody shape)."""

    title         = serializers.CharField(max_length=200)
    description   = serializers.CharField()
    cover_image   = serializers.CharField(max_length=500, required=False, allow_null=True, allow_blank=True)
    banner_image  = serializers.CharField(max_length=500, required=False, allow_null=True, allow_blank=True)
    event_type    = serializers.ChoiceField(choices=Event.EventType.choices)

    start_datetime        = serializers.DateTimeField()
    end_datetime          = serializers.DateTimeField()
    registration_url      = serializers.CharField(max_length=500, required=False, allow_null=True, allow_blank=True)
    registration_deadline = serializers.DateTimeField(required=False, allow_null=True)
    min_karma             = serializers.IntegerField(required=False, allow_null=True, min_value=0)

    venue     = EventVenueWriteSerializer()
    scope     = EventScopeWriteSerializer()
    organiser = EventOrganiserWriteSerializer()

    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        allow_empty=True,
    )

    def validate(self, data):
        if data["end_datetime"] <= data["start_datetime"]:
            raise serializers.ValidationError(
                {"end_datetime": "End datetime must be after start datetime."}
            )
        return data

    def create(self, validated_data):
        user_id = self.context["user_id"]
        now = DateTimeUtils.get_current_utc_time()

        venue_data = validated_data.pop("venue")
        scope_data = validated_data.pop("scope")
        organiser_data = validated_data.pop("organiser")
        tags_data = validated_data.pop("tags", [])

        # Determine initial status based on approval flow
        from api.events.permissions import determine_initial_status
        initial_status = determine_initial_status(
            organiser_data["organiser_type"],
            user_id,
            organiser_data.get("ci_org_id") or organiser_data.get("org_id"),
        )

        # Create the event
        event = Event.objects.create(
            id=str(uuid.uuid4()),
            title=validated_data["title"],
            slug=self._generate_unique_slug(validated_data["title"]),
            description=validated_data["description"],
            cover_image=validated_data.get("cover_image"),
            banner_image=validated_data.get("banner_image"),
            event_type=validated_data["event_type"],
            status=initial_status,
            start_datetime=validated_data["start_datetime"],
            end_datetime=validated_data["end_datetime"],
            registration_url=validated_data.get("registration_url"),
            registration_deadline=validated_data.get("registration_deadline"),
            min_karma=validated_data.get("min_karma"),
            created_by_id=user_id,
            created_at=now,
            updated_by_id=user_id,
            updated_at=now,
        )

        # Create venue
        EventVenue.objects.create(
            id=str(uuid.uuid4()),
            event=event,
            venue_type=venue_data["venue_type"],
            address=venue_data.get("address"),
            city=venue_data.get("city"),
            maps_url=venue_data.get("maps_url"),
            online_link=venue_data.get("online_link"),
            platform=venue_data.get("platform"),
            created_at=now,
            updated_at=now,
        )

        # Create scope
        EventScope.objects.create(
            id=str(uuid.uuid4()),
            event=event,
            scope=scope_data["scope"],
            target_org_id_id=scope_data.get("target_org_id"),
            target_ig_id_id=scope_data.get("target_ig_id"),
            target_ci_org_id_id=scope_data.get("target_ci_org_id"),
            target_ci_ig_id_id=scope_data.get("target_ci_ig_id"),
            created_at=now,
            updated_at=now,
        )

        # Create organiser
        EventOrganiser.objects.create(
            id=str(uuid.uuid4()),
            event=event,
            organiser_type=organiser_data["organiser_type"],
            ig_id_id=organiser_data.get("ig_id"),
            org_id_id=organiser_data.get("org_id"),
            ci_org_id_id=organiser_data.get("ci_org_id"),
            ci_ig_id_id=organiser_data.get("ci_ig_id"),
            created_at=now,
            updated_at=now,
        )

        # Create tags
        self._sync_tags(event, tags_data, now)

        return event

    def update(self, instance, validated_data):
        user_id = self.context["user_id"]
        now = DateTimeUtils.get_current_utc_time()

        venue_data = validated_data.pop("venue", None)
        scope_data = validated_data.pop("scope", None)
        organiser_data = validated_data.pop("organiser", None)
        tags_data = validated_data.pop("tags", None)

        # Track changed fields for audit log
        changed_fields = []

        # Update core event fields
        for field in [
            "title", "description", "cover_image", "banner_image",
            "event_type", "start_datetime", "end_datetime",
            "registration_url", "registration_deadline", "min_karma",
        ]:
            if field in validated_data:
                old_val = getattr(instance, field)
                new_val = validated_data[field]
                if old_val != new_val:
                    changed_fields.append(field)
                    setattr(instance, field, new_val)

        if "title" in validated_data and "title" in changed_fields:
            instance.slug = self._generate_unique_slug(validated_data["title"], exclude_id=instance.id)

        instance.updated_by_id = user_id
        instance.updated_at = now
        instance.save()

        # Update venue
        if venue_data is not None:
            venue = EventVenue.objects.filter(event=instance).first()
            if venue:
                for k, v in venue_data.items():
                    setattr(venue, k, v)
                venue.updated_at = now
                venue.save()
                changed_fields.append("venue")

        # Update scope
        if scope_data is not None:
            scope = EventScope.objects.filter(event=instance).first()
            if scope:
                scope.scope = scope_data["scope"]
                scope.target_org_id_id = scope_data.get("target_org_id")
                scope.target_ig_id_id = scope_data.get("target_ig_id")
                scope.target_ci_org_id_id = scope_data.get("target_ci_org_id")
                scope.target_ci_ig_id_id = scope_data.get("target_ci_ig_id")
                scope.updated_at = now
                scope.save()
                changed_fields.append("scope")

        # Update tags
        if tags_data is not None:
            self._sync_tags(instance, tags_data, now)
            changed_fields.append("tags")

        # Write audit log
        if changed_fields:
            EventEditLog.objects.create(
                id=str(uuid.uuid4()),
                event=instance,
                edited_by_id=user_id,
                changed_fields=changed_fields,
                edited_at=now,
            )

        return instance

    def _generate_unique_slug(self, title: str, exclude_id: str = None) -> str:
        base_slug = slugify(title)[:200]
        slug = base_slug
        counter = 1
        qs = Event.objects.filter(slug=slug)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        while qs.exists():
            slug = f"{base_slug}-{counter}"
            qs = Event.objects.filter(slug=slug)
            if exclude_id:
                qs = qs.exclude(id=exclude_id)
            counter += 1
        return slug

    def _sync_tags(self, event: Event, tag_names: list[str], now):
        """Replace all tags on an event with the given list."""
        EventTagLink.objects.filter(event=event).delete()
        for name in tag_names:
            name = name.strip().lower()
            if not name:
                continue
            tag, _ = EventTag.objects.get_or_create(
                name=name,
                defaults={"id": str(uuid.uuid4()), "created_at": now},
            )
            EventTagLink.objects.create(
                id=str(uuid.uuid4()),
                event=event,
                tag=tag,
                created_at=now,
            )


# ──────────────────────────────────────────────────
# WRITE — Collaborator invite
# ──────────────────────────────────────────────────

class CollaboratorInviteSerializer(serializers.Serializer):
    collaborator_type = serializers.ChoiceField(choices=EventCollaborator.CollaboratorType.choices)
    ig_id     = serializers.CharField(max_length=36, required=False, allow_null=True)
    org_id    = serializers.CharField(max_length=36, required=False, allow_null=True)
    ci_org_id = serializers.CharField(max_length=36, required=False, allow_null=True)
    ci_ig_id  = serializers.CharField(max_length=36, required=False, allow_null=True)
    role_label = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)


# ──────────────────────────────────────────────────
# WRITE — Co-owner add
# ──────────────────────────────────────────────────

class CoOwnerAddSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=36)
    role = serializers.ChoiceField(
        choices=EventCoOwner.CoOwnerRole.choices,
        default=EventCoOwner.CoOwnerRole.CO_OWNER,
    )
