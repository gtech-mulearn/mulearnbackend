import uuid

from django.utils.text import slugify
from django.utils import timezone
from rest_framework import serializers

from db.comic import Chapter, ChapterPage, Comic
from api.muComics.comic.serializers import MinimalUserSerializer
from api.dashboard.media_content.image_utils import resolve_image_url


# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER PAGE SERIALIZER
# ─────────────────────────────────────────────────────────────────────────────

class ChapterPageSerializer(serializers.ModelSerializer):
    """
    Serializer representing individual pages in a chapter.
    """
    class Meta:
        model = ChapterPage
        fields = ['id', 'chapter', 'page_number', 'image_key', 'created_at']
        read_only_fields = ['id', 'created_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('image_key'):
            data['image_key'] = resolve_image_url(data['image_key'], self.context.get('request'))
        return data

    def validate_page_number(self, value):
        if value < 1:
            raise serializers.ValidationError("Page number must be a positive integer starting from 1.")
        return value

    def validate_image_key(self, value):
        value = value.strip() if value else ""
        if not value:
            raise serializers.ValidationError("Image key must not be blank.")
        return value

    def validate(self, attrs):
        chapter = attrs.get('chapter') if 'chapter' in attrs else (self.instance.chapter if self.instance else None)
        page_number = attrs.get('page_number') if 'page_number' in attrs else (self.instance.page_number if self.instance else None)

        if chapter and page_number is not None:
            # Check unique constraint on (chapter, page_number) excluding deleted pages
            qs = ChapterPage.objects.filter(chapter=chapter, page_number=page_number, deleted_at__isnull=True)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise serializers.ValidationError({
                    'page_number': 'A page with this number already exists in this chapter.'
                })
        return attrs


# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER LIST (lean - for paginated lists/feeds)
# ─────────────────────────────────────────────────────────────────────────────

class ChapterListSerializer(serializers.ModelSerializer):
    """
    Lean serializer for listing chapters (e.g. comic chapter index).
    """
    class Meta:
        model = Chapter
        fields = [
            'id', 'comic', 'title', 'slug', 'chapter_number',
            'cover_image_key', 'status', 'published_at', 'created_at',
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('cover_image_key'):
            data['cover_image_key'] = resolve_image_url(data['cover_image_key'], self.context.get('request'))
        return data


# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER DETAIL (full - detail, create, or update responses)
# ─────────────────────────────────────────────────────────────────────────────

class ChapterDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for chapter retrieval.
    """
    created_by = MinimalUserSerializer(read_only=True)
    updated_by = MinimalUserSerializer(read_only=True)
    pages      = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = [
            'id', 'comic', 'title', 'slug', 'description', 'chapter_number',
            'cover_image_key', 'status', 'published_at',
            'pages',
            'created_by', 'created_at',
            'updated_by', 'updated_at',
        ]
        read_only_fields = fields

    def get_pages(self, obj):
        active_pages = obj.pages.filter(deleted_at__isnull=True).order_by('page_number')
        return ChapterPageSerializer(active_pages, many=True, context=self.context).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('cover_image_key'):
            data['cover_image_key'] = resolve_image_url(data['cover_image_key'], self.context.get('request'))
        return data


# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER WRITE (create / update input)
# ─────────────────────────────────────────────────────────────────────────────

class ChapterWriteSerializer(serializers.ModelSerializer):
    """
    Input serializer for POST /chapters/ and PATCH /chapters/<id>/.
    Caller never directly specifies slug, status, published_at, or audit fields.
    """
    class Meta:
        model = Chapter
        fields = ['comic', 'title', 'description', 'chapter_number', 'cover_image_key']
        extra_kwargs = {
            'title': {
                'required': True,
                'max_length': 150,
            },
            'chapter_number': {
                'required': True,
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
                'max_length': 255,
            },
        }

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Title must not be blank.')
        return value.strip()

    def validate_chapter_number(self, value):
        if value < 0:
            raise serializers.ValidationError('Chapter number must not be negative.')
        return value

    def _generate_unique_slug(self, title):
        """
        Generates a URL-safe slug from title.
        Appends an incrementing counter if the base slug already exists.
        Slug is truncated to 70 chars before suffix to stay within max_length=75.
        """
        base = slugify(title)[:70]
        slug = base
        counter = 1
        exclude_id = self.instance.id if self.instance else None
        while True:
            qs = Chapter.objects.filter(slug=slug)
            if exclude_id:
                qs = qs.exclude(id=exclude_id)
            if not qs.exists():
                break
            slug = f'{base}-{counter}'
            counter += 1
        return slug

    def validate(self, attrs):
        comic = attrs.get('comic') if 'comic' in attrs else (self.instance.comic if self.instance else None)
        chapter_number = attrs.get('chapter_number') if 'chapter_number' in attrs else (self.instance.chapter_number if self.instance else None)

        if comic and chapter_number is not None:
            # Check unique constraint on (comic, chapter_number) excluding deleted chapters
            qs = Chapter.objects.filter(comic=comic, chapter_number=chapter_number, deleted_at__isnull=True)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise serializers.ValidationError({
                    'chapter_number': 'A chapter with this number already exists for this comic.'
                })
        return attrs

    def create(self, validated_data):
        user_id = self.context['user_id']
        now     = timezone.now()

        validated_data['id']            = str(uuid.uuid4())
        validated_data['slug']          = self._generate_unique_slug(validated_data['title'])
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id
        validated_data['created_at']    = now
        validated_data['updated_at']    = now
        return Chapter.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user_id = self.context['user_id']
        now     = timezone.now()

        # Chapter parent comic cannot be modified on update
        if 'comic' in validated_data:
            if validated_data['comic'] != instance.comic:
                raise serializers.ValidationError({'comic': 'Chapter parent comic cannot be modified.'})
            validated_data.pop('comic')

        # Re-generate slug only when title changes
        if 'title' in validated_data and validated_data['title'] != instance.title:
            validated_data['slug'] = self._generate_unique_slug(validated_data['title'])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.updated_by_id = user_id
        instance.updated_at    = now

        # Only write columns this PATCH actually touched.
        changed_fields = list(validated_data.keys())
        if 'title' in changed_fields:
            changed_fields.append('slug')
        changed_fields += ['updated_by', 'updated_at']

        instance.save(update_fields=changed_fields)
        return instance

