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
    created_by   = MinimalUserSerializer(read_only=True)
    genres       = serializers.SerializerMethodField()
    contributors = serializers.SerializerMethodField()

    class Meta:
        model = Comic
        fields = [
            'id', 'title', 'slug', 'cover_image_key',
            'status', 'like_count', 'comment_count', 'bookmark_count',
            'published_at', 'created_by', 'created_at',
            'genres', 'contributors',
        ]

    def get_genres(self, obj):
        links = obj.genre_links.all()
        active_genres = [link.genre for link in links if link.genre.is_active]
        return MinimalGenreSerializer(active_genres, many=True).data

    def get_contributors(self, obj):
        links = obj.contributor_links.select_related('user').all()
        return ContributorSerializer(links, many=True).data



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
        # Option A: only active genres shown; inactive genre hides from comic detail
        links = obj.genre_links.select_related('genre').filter(genre__is_active=True)
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
    On create, `creator_muid` specifies the comic owner (resolved to a User).
    """
    creator_muid = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = Comic
        fields = ['title', 'description', 'cover_image_key', 'creator_muid']
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

    def validate_creator_muid(self, value):
        try:
            return User.objects.get(muid=value, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError(f'No active user with muid "{value}" found.')

    def validate(self, attrs):
        # creator_muid is required on create only
        if not self.instance and 'creator_muid' not in attrs:
            raise serializers.ValidationError({'creator_muid': 'This field is required when creating a comic.'})
        return attrs

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
        # On update: exclude the current comic so its own slug is not treated as a collision.
        # On create: self.instance is None, so no exclusion is applied.
        exclude_id = self.instance.id if self.instance else None
        while True:
            qs = Comic.objects.filter(slug=slug)
            if exclude_id:
                qs = qs.exclude(id=exclude_id)
            if not qs.exists():
                break
            slug = f'{base}-{counter}'
            counter += 1
        return slug

    def create(self, validated_data):
        user_id = self.context['user_id']
        creator = validated_data.pop('creator_muid')  # User object from validate_creator_muid
        now     = timezone.now()

        validated_data['id']           = str(uuid.uuid4())
        validated_data['slug']         = self._generate_unique_slug(validated_data['title'])
        validated_data['created_by_id'] = creator.id   # specified creator, not the admin
        validated_data['updated_by_id'] = user_id      # admin who performed the action
        validated_data['created_at']   = now
        validated_data['updated_at']   = now
        return Comic.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user_id = self.context['user_id']
        validated_data.pop('creator_muid', None)  # creator is not changeable after creation
        now     = timezone.now()

        # Re-generate slug only when title changes
        if 'title' in validated_data and validated_data['title'] != instance.title:
            validated_data['slug'] = self._generate_unique_slug(validated_data['title'])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.updated_by_id = user_id
        instance.updated_at    = now

        # Only write columns this PATCH actually touched.
        # 'status' and 'published_at' are intentionally absent — this prevents
        # a concurrent publish/archive from being silently reverted.
        changed_fields = list(validated_data.keys())
        if 'title' in changed_fields:
            changed_fields.append('slug')   # slug is derived from title
        changed_fields += ['updated_by', 'updated_at']

        instance.save(update_fields=changed_fields)
        return instance


# ─────────────────────────────────────────────────────────────────────────────
# CONTRIBUTOR MANAGEMENT  (add / list / update-role / remove)
# ─────────────────────────────────────────────────────────────────────────────

# Valid roles that can be assigned via the API.
# CREATOR is intentionally excluded — it is tracked via comic.created_by.
_ASSIGNABLE_CONTRIBUTOR_CHOICES = [
    (ct.value, ct.label)
    for ct in ComicContributorLink.ContributorType
    if ct != ComicContributorLink.ContributorType.CREATOR
]


class ContributorWriteSerializer(serializers.Serializer):
    """
    Input for POST /comics/{comicId}/contributors/.
    Resolves `muid` → User object during validation so create() receives a
    ready-to-use User instance.
    """
    muid = serializers.CharField()
    role = serializers.ChoiceField(choices=_ASSIGNABLE_CONTRIBUTOR_CHOICES)

    def validate_muid(self, value):
        try:
            return User.objects.get(muid=value, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError(f'No Active user with muid "{value}" not found.')

    def create(self, validated_data):
        comic   = self.context['comic']
        user    = validated_data['muid']   # User object — resolved in validate_muid
        role    = validated_data['role']
        user_id = self.context['user_id']
        now     = timezone.now()

        return ComicContributorLink.objects.create(
            id               = str(uuid.uuid4()),
            comic            = comic,
            user             = user,
            contributor_type = role,
            created_by_id    = user_id,
            created_at       = now,
        )


class ContributorRoleUpdateSerializer(serializers.Serializer):
    """Input for PATCH /comics/{comicId}/contributors/{contributorId}/."""
    role = serializers.ChoiceField(choices=_ASSIGNABLE_CONTRIBUTOR_CHOICES)


class ContributorListSerializer(serializers.ModelSerializer):
    """
    Output shape for GET /comics/{comicId}/contributors/.
    Flattens the ComicContributorLink → User / Comic relations.
    """
    contributor_id = serializers.CharField(source='id')
    user_id        = serializers.CharField(source='user.id')
    role           = serializers.CharField(source='contributor_type')
    name           = serializers.CharField(source='user.full_name')
    comic_name     = serializers.CharField(source='comic.title')

    class Meta:
        model  = ComicContributorLink
        fields = ['contributor_id', 'user_id', 'role', 'name', 'comic_name']


# ─────────────────────────────────────────────────────────────────────────────
# GENRE MANAGEMENT  (admin read / write)
# ─────────────────────────────────────────────────────────────────────────────

class GenreReadSerializer(serializers.ModelSerializer):
    """Output shape for genre list / detail responses."""

    class Meta:
        model  = Genre
        fields = ['id', 'name', 'slug', 'is_active', 'created_at', 'updated_at']


class GenreWriteSerializer(serializers.ModelSerializer):
    """
    Input serializer for POST /comics/genres/ and PATCH /comics/genres/<id>/.
    Caller only sends `name`; slug and audit fields are set internally.
    """

    class Meta:
        model  = Genre
        fields = ['name']
        extra_kwargs = {
            'name': {
                'required':    True,
                'max_length':  75,
                'allow_blank': False,
            },
        }

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Name must not be blank.')
        return value.strip()

    def _generate_unique_slug(self, name):
        """
        URL-safe slug from name. Appends an incrementing counter on collision.
        Truncated to 70 chars before suffix to stay within max_length=75.
        On update, excludes the current genre's own slug from collision check.
        """
        base       = slugify(name)[:70]
        slug       = base
        counter    = 1
        exclude_id = self.instance.id if self.instance else None

        while True:
            qs = Genre.objects.filter(slug=slug)
            if exclude_id:
                qs = qs.exclude(id=exclude_id)
            if not qs.exists():
                break
            slug    = f'{base}-{counter}'
            counter += 1
        return slug

    def create(self, validated_data):
        user_id = self.context['user_id']
        now     = timezone.now()

        validated_data['id']            = str(uuid.uuid4())
        validated_data['slug']          = self._generate_unique_slug(validated_data['name'])
        validated_data['is_active']     = True
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id
        validated_data['created_at']    = now
        validated_data['updated_at']    = now

        return Genre.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user_id = self.context['user_id']
        now     = timezone.now()

        if 'name' in validated_data and validated_data['name'] != instance.name:
            validated_data['slug'] = self._generate_unique_slug(validated_data['name'])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.updated_by_id = user_id
        instance.updated_at    = now

        changed_fields = list(validated_data.keys())
        if 'name' in changed_fields:
            changed_fields.append('slug')
        changed_fields += ['updated_by', 'updated_at']

        instance.save(update_fields=changed_fields)
        return instance


# ─────────────────────────────────────────────────────────────────────────────
# COMIC GENRE LINK MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

class ComicGenreAssignSerializer(serializers.Serializer):
    """
    Input serializer for POST /comics/{comicId}/genres/.
    Validates that:
    - The genre exists.
    - The genre is active (is_active=True).
    - The genre is not already assigned to this comic.
    """
    genre_id = serializers.CharField()

    def validate_genre_id(self, value):
        try:
            genre = Genre.objects.get(id=value)
        except Genre.DoesNotExist:
            raise serializers.ValidationError(f"Genre with id '{value}' not found.")

        if not genre.is_active:
            raise serializers.ValidationError("Cannot assign an inactive genre.")

        comic = self.context['comic']
        if ComicGenreLink.objects.filter(comic=comic, genre=genre).exists():
            raise serializers.ValidationError("This genre is already assigned to the comic.")

        return genre

    def create(self, validated_data):
        comic   = self.context['comic']
        genre   = validated_data['genre_id'] # This is a Genre instance populated in validate_genre_id
        user_id = self.context['user_id']
        now     = timezone.now()

        return ComicGenreLink.objects.create(
            id=str(uuid.uuid4()),
            comic=comic,
            genre=genre,
            created_by_id=user_id,
            created_at=now,
        )


