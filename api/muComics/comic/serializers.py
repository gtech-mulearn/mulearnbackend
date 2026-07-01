"""
Serializers for the Comic CRUD module.

Shapes:
  ComicListItemSerializer   – lean, used in paginated list responses
  ComicDetailSerializer     – full, used in detail / create / update responses
  ComicWriteSerializer      – input, used for POST and PATCH
"""

import uuid

from django.utils.text import slugify
from django.utils import timezone
from rest_framework import serializers

from db.comic import Comic, Genre, ComicContributorLink, ComicGenreLink
from db.user import User


# ─────────────────────────────────────────────────────────────────────────────
# MINIMAL NESTED SHAPES
# ─────────────────────────────────────────────────────────────────────────────

class MinimalUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'full_name', 'muid']


class MinimalGenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name', 'slug']


class ContributorSerializer(serializers.ModelSerializer):
    user = MinimalUserSerializer(read_only=True)

    class Meta:
        model = ComicContributorLink
        fields = ['id', 'user', 'contributor_type', 'created_at']


# ─────────────────────────────────────────────────────────────────────────────
# COMIC LIST (lean — for paginated feeds)
# ─────────────────────────────────────────────────────────────────────────────

class ComicListItemSerializer(serializers.ModelSerializer):
    created_by = MinimalUserSerializer(read_only=True)

    class Meta:
        model = Comic
        fields = [
            'id', 'title', 'slug', 'cover_image_key',
            'status', 'like_count', 'comment_count', 'bookmark_count',
            'published_at', 'created_by', 'created_at',
        ]


# ─────────────────────────────────────────────────────────────────────────────
# COMIC DETAIL (full — for detail / create / update responses)
# ─────────────────────────────────────────────────────────────────────────────

class ComicDetailSerializer(serializers.ModelSerializer):
    created_by  = MinimalUserSerializer(read_only=True)
    updated_by  = MinimalUserSerializer(read_only=True)
    genres      = serializers.SerializerMethodField()
    contributors = serializers.SerializerMethodField()

    class Meta:
        model = Comic
        fields = [
            'id', 'title', 'slug', 'description', 'cover_image_key',
            'status', 'like_count', 'comment_count', 'bookmark_count',
            'published_at',
            'genres', 'contributors',
            'created_by', 'created_at',
            'updated_by', 'updated_at',
        ]

    def get_genres(self, obj):
        links = obj.genre_links.select_related('genre').all()
        return MinimalGenreSerializer(
            [link.genre for link in links], many=True
        ).data

    def get_contributors(self, obj):
        links = obj.contributor_links.select_related('user').all()
        return ContributorSerializer(links, many=True).data


# ─────────────────────────────────────────────────────────────────────────────
# COMIC WRITE  (create / update input)
# ─────────────────────────────────────────────────────────────────────────────

class ComicWriteSerializer(serializers.ModelSerializer):
    """
    Input serializer for POST /comics/ and PATCH /comics/<id>/.
    The caller never sends: slug, status, *_count, published_at, or audit fields.
    """

    class Meta:
        model = Comic
        fields = ['title', 'description', 'cover_image_key']
        extra_kwargs = {
            'title': {
                'required': True,
                'max_length': 150,  # matches Comic.title max_length in db/comic.py
            },
            'description': {
                'required': False,
                'allow_null': True,
                'allow_blank': True,
            },
            'cover_image_key': {
                'required': False,
                'allow_null': True,
                'allow_blank': True,
                'max_length': 255,  # matches Comic.cover_image_key max_length in db/comic.py
            },
        }

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Title must not be blank.')
        return value.strip()

    def _generate_unique_slug(self, title):
        """
        Generates a URL-safe slug from title.
        Appends an incrementing counter if the base slug already exists
        (same pattern as EventWriteSerializer._generate_unique_slug).
        Slug is truncated to 70 chars before suffix to stay within max_length=75.
        """
        base = slugify(title)[:70]
        slug = base
        counter = 1
        while Comic.objects.filter(slug=slug).exists():
            slug = f'{base}-{counter}'
            counter += 1
        return slug

    def create(self, validated_data):
        user_id = self.context['user_id']
        now     = timezone.now()

        validated_data['id']           = str(uuid.uuid4())
        validated_data['slug']         = self._generate_unique_slug(validated_data['title'])
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id
        validated_data['created_at']   = now
        validated_data['updated_at']   = now
        return Comic.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user_id = self.context['user_id']
        now     = timezone.now()

        # Re-generate slug only when title changes
        if 'title' in validated_data and validated_data['title'] != instance.title:
            validated_data['slug'] = self._generate_unique_slug(validated_data['title'])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.updated_by_id = user_id
        instance.updated_at    = now
        instance.save()
        return instance
