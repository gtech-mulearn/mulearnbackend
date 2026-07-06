import uuid

from django.db import models
from django.conf import settings

from .user import User
from .comic import Comic


class ComicComment(models.Model):

    id         = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)

    comic      = models.ForeignKey(
        Comic, on_delete=models.CASCADE,
        db_column='comic_id', related_name='comments'
    )
    chapter_id = models.CharField(max_length=36, null=True, blank=True)
    parent     = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        db_column='parent_id', related_name='replies'
    )
    user       = models.ForeignKey(
        User, on_delete=models.CASCADE,
        db_column='user_id', related_name='comic_comments'
    )
    message    = models.TextField()

    # Soft delete
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='deleted_by', related_name='comic_comment_deleted_by'
    )

    # Audit
    updated_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='updated_by', related_name='comic_comment_updated_by'
    )
    updated_at = models.DateTimeField()

    created_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='created_by', related_name='comic_comment_created_by'
    )
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'comic_comment'
        indexes = [
            models.Index(fields=['comic', 'created_at'], name='idx_comic_comment_comic'),
            models.Index(fields=['chapter_id', 'created_at'], name='idx_comic_comment_chapter'),
            models.Index(fields=['parent'], name='idx_comic_comment_parent'),
            models.Index(fields=['user'], name='idx_comic_comment_user'),
        ]

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    @property
    def is_edited(self):
        if self.updated_at and self.created_at:
            return self.updated_at > self.created_at
        return False
