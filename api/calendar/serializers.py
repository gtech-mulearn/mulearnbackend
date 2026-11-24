from rest_framework import serializers

from db.mentor import MentorshipSession, MentorshipSessionUserLink
from db.events import Event


class MentorshipSessionCalendarSerializer(serializers.ModelSerializer):
    mentor_name = serializers.SerializerMethodField()
    mentee_count = serializers.SerializerMethodField()

    class Meta:
        model = MentorshipSession
        fields = [
            'id',
            'title',
            'description',
            'mode',
            'starts_at',
            'ends_at',
            'status',
            'meeting_link',
            'venue',
            'mentor_name',
            'mentee_count',
        ]

    @staticmethod
    def _links(obj, role):
        """
        This session's participant links with `role`, from the views'
        SESSION_PREFETCH when present (the .filter() calls here skipped it:
        two queries per session). The column compares case-insensitively.
        """
        if 'participant_links' in getattr(obj, '_prefetched_objects_cache', {}):
            return [
                link for link in obj.participant_links.all()
                if (link.participant_role or '').upper() == role
            ]
        return None

    def get_mentor_name(self, obj):
        role = MentorshipSessionUserLink.ParticipantRole.MENTOR
        links = self._links(obj, role)
        if links is not None:
            # .first() picked the lowest pk
            mentor_link = min(links, key=lambda link: link.pk) if links else None
        else:
            mentor_link = obj.participant_links.filter(
                participant_role=role
            ).select_related('user').first()
        if mentor_link:
            return mentor_link.user.full_name
        # Fallback for sessions created before the MENTOR participant link
        # was auto-created at session-creation time.
        return obj.created_by.full_name if obj.created_by_id else None

    def get_mentee_count(self, obj):
        role = MentorshipSessionUserLink.ParticipantRole.MENTEE
        links = self._links(obj, role)
        if links is not None:
            return len(links)
        return obj.participant_links.filter(participant_role=role).count()


class EventCalendarSerializer(serializers.ModelSerializer):
    ig_name = serializers.SerializerMethodField()
    org_name = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id',
            'title',
            'slug',
            'status',
            'start_datetime',
            'end_datetime',
            'venue_type',
            'venue_city',
            'venue_online_link',
            'scope',
            'cover_image',
            'organiser_type',
            'is_featured',
            'interest_count',
            'ig_name',
            'org_name',
        ]

    def get_ig_name(self, obj):
        return obj.scope_ig.name if obj.scope_ig else None

    def get_org_name(self, obj):
        return obj.scope_org.title if obj.scope_org else None
