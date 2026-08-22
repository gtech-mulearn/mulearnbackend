from rest_framework import serializers

from db.notification import Notification, BroadcastNotification


# ─────────────────────────────────────────────────────────────────────────────
# New v2 serializer — matches the new notification table schema (PRD §5.1)
# ─────────────────────────────────────────────────────────────────────────────

class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializes a Notification row for the user-facing feed.
    The actor field exposes id + full_name without revealing sensitive user data.
    """
    actor = serializers.SerializerMethodField()

    class Meta:
        model  = Notification
        fields = [
            'id',
            'type',
            'category',
            'title',
            'description',
            'entity_type',
            'entity_id',
            'is_read',
            'is_archived',
            'created_at',
            'read_at',
            'actor',
        ]

    def get_actor(self, obj):
        """Returns minimal actor info — who triggered this notification."""
        if not obj.actor_id:
            return None
        return {
            'id':          str(obj.actor_id),
            'full_name':   getattr(obj.actor, 'full_name', None),
            'muid':        getattr(obj.actor, 'muid', None),
            'profile_pic': getattr(obj.actor, 'profile_pic', None),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Legacy broadcast serializers — kept for backward-compat
# These serve the existing broadcast endpoints which are still active.
# ─────────────────────────────────────────────────────────────────────────────

class BroadcastNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = BroadcastNotification
        fields = [
            'id', 'title', 'description', 'url',
            'target_type', 'target_id',
            'created_at', 'expires_at', 'created_by',
        ]


class BroadcastNotificationAdminSerializer(serializers.ModelSerializer):
    """
    Extended serializer for admin CRUD on BroadcastNotification.
    Adds a `target_details` field that resolves the human-readable name of
    the target entity from target_type + target_id.
    """
    target_details  = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model  = BroadcastNotification
        fields = [
            'id', 'title', 'description', 'url',
            'target_type', 'target_id', 'target_details',
            'created_by', 'created_by_name',
            'created_at', 'expires_at',
        ]
        read_only_fields = ['id', 'created_at', 'created_by', 'created_by_name', 'target_details']

    def get_target_details(self, obj):
        tt  = obj.target_type
        tid = obj.target_id

        if tt == 'global':
            return {'type': 'global', 'name': 'Global (All Users)'}
        if not tid:
            return {'type': tt, 'name': None}

        try:
            if tt == 'campus':
                from db.organization import Organization
                org = Organization.objects.filter(id=tid).first()
                return {'type': 'campus', 'name': org.title if org else f'Unknown Campus ({tid})'}

            if tt == 'interest_group':
                from db.task import InterestGroup
                ig = InterestGroup.objects.filter(id=tid).first()
                return {'type': 'interest_group', 'name': ig.name if ig else f'Unknown IG ({tid})'}

            if tt == 'campus_ig':
                from db.campus import CampusIGChapter
                chapter = CampusIGChapter.objects.select_related('org', 'ig').filter(id=tid).first()
                if chapter:
                    return {'type': 'campus_ig', 'name': f'{chapter.org.title} — {chapter.ig.name}'}
                return {'type': 'campus_ig', 'name': f'Unknown Chapter ({tid})'}

            if tt in ('event_interest', 'event_coowners'):
                from db.events import Event
                event = Event.objects.filter(id=tid).first()
                return {'type': tt, 'name': event.title if event else f'Unknown Event ({tid})'}

        except Exception:
            pass

        return {'type': tt, 'name': tid}


class BroadcastNotificationWriteSerializer(serializers.ModelSerializer):
    """Write-only serializer for Create and Update of BroadcastNotification."""
    class Meta:
        model  = BroadcastNotification
        fields = ['title', 'description', 'url', 'expires_at']
