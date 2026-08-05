"""
Serializers for the MediaContent module.

Read serializers  — returned in GET responses; include computed `is_upcoming`.
Write serializers — used for POST (create) and PATCH (partial update); validate
                    type-specific required fields, date formats, and enum values.
"""
import uuid
from datetime import date

from rest_framework import serializers

from api.dashboard.media_content.image_utils import resolve_image_url
from db.events import MediaContent, IgMediaContentLink
from db.task import InterestGroup


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _compute_status(record_date: date) -> str:
    """Compute status based on date relative to today."""
    today = date.today()
    if record_date > today:
        return 'upcoming'
    elif record_date == today:
        return 'ongoing'
    else:
        return 'completed'


# ─────────────────────────────────────────────────────────────────────────────
# READ serializers
# ─────────────────────────────────────────────────────────────────────────────

class OfficeHoursReadSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for Office Hours sessions.
    Exposes all Office Hours fields plus a computed ``status`` flag.
    """
    status = serializers.SerializerMethodField()
    poster_thumbnail = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()

    class Meta:
        model = MediaContent
        fields = [
            'id',
            'title',
            'performer',
            'designation',
            'description',
            'date',
            'time',
            'link',
            'interest_groups',
            'poster_thumbnail',
            'status',
            'created_at',
            'updated_at',
        ]

    def get_status(self, obj):
        return _compute_status(obj.date)

    def get_poster_thumbnail(self, obj):
        return resolve_image_url(obj.poster_thumbnail, self.context.get('request'))

    def get_interest_groups(self, obj):
        link_ids = obj.interest_groups or []
        if not link_ids:
            return []
        links = IgMediaContentLink.objects.filter(
            id__in=link_ids
        ).select_related('interest_group')
        names_by_id = {link.id: link.interest_group.name for link in links}
        return [names_by_id[link_id] for link_id in link_ids if link_id in names_by_id]


class GrabYourSuperpowersReadSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for Grab Your Superpowers sessions.
    Session name (``title``), date, time, description, speaker details
    (``performer``/``designation``), hosting college (``campus``), and link.
    """
    status = serializers.SerializerMethodField()

    class Meta:
        model = MediaContent
        fields = [
            'id',
            'title',
            'date',
            'time',
            'description',
            'performer',
            'designation',
            'campus',
            'link',
            'status',
            'created_at',
            'updated_at',
        ]

    def get_status(self, obj):
        return _compute_status(obj.date)


class SaltMangoTreeReadSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for Salt Mango Tree episodes.
    Exposes topic (stored as ``title``), campus, zone, and ``status``.
    """
    # CMS used "topic"; we alias `title` → `topic` in the response.
    topic = serializers.CharField(source='title')
    status = serializers.SerializerMethodField()

    class Meta:
        model = MediaContent
        fields = [
            'id',
            'topic',
            'campus',
            'zone',
            'date',
            'time',
            'description',
            'link',
            'status',
            'created_at',
            'updated_at',
        ]

    def get_status(self, obj):
        return _compute_status(obj.date)


class InspirationStationReadSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for Inspiration Station Radio episodes.
    Same structure as SMT — topic (``title``), campus, zone, ``status``.
    """
    topic = serializers.CharField(source='title')
    status = serializers.SerializerMethodField()

    class Meta:
        model = MediaContent
        fields = [
            'id',
            'topic',
            'campus',
            'zone',
            'date',
            'time',
            'description',
            'link',
            'status',
            'created_at',
            'updated_at',
        ]

    def get_status(self, obj):
        return _compute_status(obj.date)


# ─────────────────────────────────────────────────────────────────────────────
# WRITE serializers
# ─────────────────────────────────────────────────────────────────────────────

class OfficeHoursWriteSerializer(serializers.Serializer):
    """
    Write serializer for Office Hours sessions (POST / PATCH).

    Date format accepted: DD/MM/YYYY (matches the CMS schema).
    It is converted to a Python ``date`` object for DB storage.
    """
    title            = serializers.CharField(max_length=300)
    date             = serializers.CharField(
        help_text='Format: DD/MM/YYYY'
    )
    time             = serializers.TimeField(
        input_formats=['%H:%M', '%H:%M:%S'],
        help_text='Format: HH:MM (24h)'
    )
    performer        = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True)
    designation      = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True)
    description      = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    link             = serializers.URLField(max_length=500, required=False, allow_blank=True, allow_null=True)
    interest_groups  = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True
    )
    poster_thumbnail = serializers.CharField(max_length=512, required=False, allow_blank=True, allow_null=True)

    def validate_date(self, value):
        from datetime import datetime
        try:
            return datetime.strptime(value, '%d/%m/%Y').date()
        except ValueError:
            raise serializers.ValidationError(
                "Invalid date format. Expected DD/MM/YYYY (e.g. 27/06/2025)."
            )

    def validate_interest_groups(self, value):
        """`value` is a list of interest_group ids. Every id must resolve to
        an existing InterestGroup."""
        if not value:
            return value
        found_ids = set(
            InterestGroup.objects.filter(id__in=value).values_list('id', flat=True)
        )
        unknown_ids = [ig_id for ig_id in value if ig_id not in found_ids]
        if unknown_ids:
            raise serializers.ValidationError(
                f"Unknown interest group id(s): {', '.join(unknown_ids)}."
            )
        return value

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        value['content_type'] = MediaContent.ContentType.OFFICE_HOURS
        return value


class _EpisodeWriteSerializer(serializers.Serializer):
    """
    Shared base for SMT and Inspiration Station write serializers.
    Date format accepted: YYYY-MM-DD (matches the CMS schema).
    """
    topic       = serializers.CharField(max_length=300)          # maps → title
    campus      = serializers.CharField(max_length=200)
    zone        = serializers.ChoiceField(
        choices=MediaContent.Zone.choices, required=False, allow_null=True
    )
    date        = serializers.DateField(
        input_formats=['%Y-%m-%d'],
        help_text='Format: YYYY-MM-DD'
    )
    time        = serializers.TimeField(
        input_formats=['%H:%M', '%H:%M:%S'],
        help_text='Format: HH:MM (24h)'
    )
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    link        = serializers.URLField(max_length=500, required=False, allow_blank=True, allow_null=True)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        # Remap "topic" → "title" so it aligns with the DB column name
        if 'topic' in value:
            value['title'] = value.pop('topic')
        return value


class SaltMangoTreeWriteSerializer(_EpisodeWriteSerializer):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        value['content_type'] = MediaContent.ContentType.SALT_MANGO_TREE
        return value


class InspirationStationWriteSerializer(_EpisodeWriteSerializer):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        value['content_type'] = MediaContent.ContentType.INSPIRATION_STATION
        return value


class GrabYourSuperpowersWriteSerializer(serializers.Serializer):
    """
    Write serializer for Grab Your Superpowers sessions (POST / PATCH).

    Date format accepted: YYYY-MM-DD. Time format accepted: HH:MM (24h).
    """
    title       = serializers.CharField(max_length=300)  # session name
    date        = serializers.DateField(
        input_formats=['%Y-%m-%d'],
        help_text='Format: YYYY-MM-DD'
    )
    time        = serializers.TimeField(
        input_formats=['%H:%M', '%H:%M:%S'],
        help_text='Format: HH:MM (24h)'
    )
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    performer   = serializers.CharField(
        max_length=200, required=False, allow_blank=True, allow_null=True
    )  # speaker name
    designation = serializers.CharField(
        max_length=200, required=False, allow_blank=True, allow_null=True
    )  # speaker designation/role
    campus      = serializers.CharField(max_length=200)  # conducted by which college
    link        = serializers.URLField(max_length=500, required=False, allow_blank=True, allow_null=True)  # meet link

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        value['content_type'] = MediaContent.ContentType.GRAB_YOUR_SUPERPOWERS
        return value
