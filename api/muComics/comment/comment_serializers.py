from rest_framework import serializers

from db.user import User


class CommentUserSerializer(serializers.ModelSerializer):
    """Lightweight user info embedded in comment responses."""
    profile_pic = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'full_name', 'muid', 'profile_pic']

    def get_profile_pic(self, obj):
        return obj.profile_pic


class CommentReplySerializer(serializers.Serializer):
    """Single reply (no further nesting)."""
    id = serializers.CharField()
    parent_id = serializers.CharField()
    user = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()
    is_edited = serializers.BooleanField()
    is_deleted = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_user(self, obj):
        return CommentUserSerializer(obj.user).data

    def get_message(self, obj):
        if obj.is_deleted:
            return "[deleted]"
        return obj.message

    def get_is_deleted(self, obj):
        return obj.is_deleted

    def get_is_owner(self, obj):
        request_user_id = self.context.get('user_id')
        if not request_user_id:
            return False
        return obj.user_id == request_user_id


class CommentListSerializer(serializers.Serializer):
    """Top-level comment with nested replies."""
    id = serializers.CharField()
    comic_id = serializers.CharField()
    chapter_id = serializers.CharField(allow_null=True)
    parent_id = serializers.CharField(allow_null=True)
    user = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()
    is_edited = serializers.BooleanField()
    is_deleted = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    reply_count = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_user(self, obj):
        return CommentUserSerializer(obj.user).data

    def get_message(self, obj):
        if obj.is_deleted:
            return "[deleted]"
        return obj.message

    def get_is_deleted(self, obj):
        return obj.is_deleted

    def get_is_owner(self, obj):
        request_user_id = self.context.get('user_id')
        if not request_user_id:
            return False
        return obj.user_id == request_user_id

    def get_reply_count(self, obj):
        return obj.replies.filter(deleted_at__isnull=True).count()

    def get_replies(self, obj):
        active_replies = obj.replies.filter(
            deleted_at__isnull=True
        ).select_related('user').order_by('created_at')
        return CommentReplySerializer(
            active_replies, many=True, context=self.context
        ).data


class CommentCreateSerializer(serializers.Serializer):
    """Validates POST body for comment creation."""
    message = serializers.CharField(min_length=1, max_length=2000)
    parent_id = serializers.CharField(required=False, allow_null=True, default=None)

    def validate_message(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Message cannot be empty or whitespace only.")
        return value


class CommentUpdateSerializer(serializers.Serializer):
    """Validates PATCH body for comment editing."""
    message = serializers.CharField(min_length=1, max_length=2000)

    def validate_message(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Message cannot be empty or whitespace only.")
        return value


class AdminCommentListSerializer(serializers.Serializer):
    """Admin view — flat list with extra metadata."""
    id = serializers.CharField()
    comic_id = serializers.CharField()
    comic_title = serializers.SerializerMethodField()
    chapter_id = serializers.CharField(allow_null=True)
    chapter_title = serializers.SerializerMethodField()
    parent_id = serializers.CharField(allow_null=True)
    user = serializers.SerializerMethodField()
    message = serializers.CharField()
    is_edited = serializers.BooleanField()
    is_deleted = serializers.SerializerMethodField()
    deleted_at = serializers.DateTimeField(allow_null=True)
    deleted_by_user = serializers.SerializerMethodField()
    reply_count = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_comic_title(self, obj):
        return obj.comic.title if obj.comic else None

    def get_chapter_title(self, obj):
        if not obj.chapter_id:
            return None
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT title FROM chapter WHERE id = %s", [obj.chapter_id])
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def get_user(self, obj):
        return CommentUserSerializer(obj.user).data

    def get_is_deleted(self, obj):
        return obj.is_deleted

    def get_deleted_by_user(self, obj):
        if not obj.deleted_by:
            return None
        return {
            "id": obj.deleted_by.id,
            "full_name": obj.deleted_by.full_name,
            "muid": obj.deleted_by.muid,
        }

    def get_reply_count(self, obj):
        return obj.replies.count()
