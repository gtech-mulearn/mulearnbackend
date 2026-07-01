import uuid

from django.db import models
from django.conf import settings

from .user import User


class Comic(models.Model):

    class Status(models.TextChoices):
        DRAFT     = 'draft',     'Draft'
        PUBLISHED = 'published', 'Published'
        ARCHIVED  = 'archived',  'Archived'

    id              = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    title           = models.CharField(max_length=150)
    slug            = models.CharField(max_length=180, unique=True)
    description     = models.TextField(blank=True, null=True)
    cover_image_key = models.CharField(max_length=255, blank=True, null=True)  # S3 object key

    status          = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT
    )

    like_count      = models.PositiveIntegerField(default=0)
    comment_count   = models.PositiveIntegerField(default=0)
    bookmark_count  = models.PositiveIntegerField(default=0)

    published_at    = models.DateTimeField(blank=True, null=True)

    # Soft delete
    deleted_at      = models.DateTimeField(blank=True, null=True)
    deleted_by      = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='deleted_by', related_name='comic_deleted_by'
    )

    # Audit
    updated_by      = models.ForeignKey(
        User, on_delete=models.CASCADE,
        db_column='updated_by', related_name='comic_updated_by'
    )
    updated_at      = models.DateTimeField()

    created_by      = models.ForeignKey(
        User, on_delete=models.CASCADE,
        db_column='created_by', related_name='comic_created_by'
    )
    created_at      = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'comic'
        indexes = [
            models.Index(fields=['status', 'created_at'], name='idx_comic_status_created'),
            models.Index(fields=['created_by'],            name='idx_comic_created_by'),
        ]


class Genre(models.Model):

    id         = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    name       = models.CharField(max_length=75, unique=True)
    slug       = models.CharField(max_length=90, unique=True)

    # Audit
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        db_column='updated_by', related_name='genre_updated_by'
    )
    updated_at = models.DateTimeField()

    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        db_column='created_by', related_name='genre_created_by'
    )
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'genre'


class ComicGenreLink(models.Model):

    id         = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    comic      = models.ForeignKey(
        Comic, on_delete=models.CASCADE,
        db_column='comic_id', related_name='genre_links'
    )
    genre      = models.ForeignKey(
        Genre, on_delete=models.CASCADE,
        db_column='genre_id', related_name='comic_links'
    )

    # Audit
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        db_column='created_by', related_name='comic_genre_link_created_by'
    )
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'comic_genre_link'
        unique_together = [('comic', 'genre')]
        indexes = [
            models.Index(fields=['genre'], name='idx_comic_genre_genre'),
        ]


class ComicContributorLink(models.Model):

    class ContributorType(models.TextChoices):
        CREATOR  = 'creator',  'Creator'
        WRITER   = 'writer',   'Writer'
        ARTIST   = 'artist',   'Artist'
        COLORIST = 'colorist', 'Colorist'
        EDITOR   = 'editor',   'Editor'

    id               = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    comic            = models.ForeignKey(
        Comic, on_delete=models.CASCADE,
        db_column='comic_id', related_name='contributor_links'
    )
    user             = models.ForeignKey(
        User, on_delete=models.CASCADE,
        db_column='user_id', related_name='comic_contributor_links'
    )
    contributor_type = models.CharField(
        max_length=10, choices=ContributorType.choices
    )

    # Audit
    created_by       = models.ForeignKey(
        User, on_delete=models.CASCADE,
        db_column='created_by', related_name='comic_contributor_link_created_by'
    )
    created_at       = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'comic_contributor_link'
        unique_together = [('comic', 'user', 'contributor_type')]
        indexes = [
            models.Index(fields=['user'],                      name='idx_contributor_user'),
            models.Index(fields=['comic', 'contributor_type'], name='idx_contributor_comic_type'),
        ]
