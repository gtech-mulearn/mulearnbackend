from django.db import transaction, IntegrityError
from django.db.models import F
from django.utils import timezone
from rest_framework import serializers

from db.comic import Comic, ComicLikeLink, ComicBookmarkLink, ComicReadingProgress, Chapter
from utils.permission import JWTUtils


class ComicInteractionValidationMixin:
    """Mixin to validate that a comic is published and active."""
    
    def validate_comic_id(self, value):
        comic = Comic.objects.filter(
            id=value,
            status=Comic.Status.PUBLISHED,
            deleted_at__isnull=True
        ).first()
        if not comic:
            raise serializers.ValidationError("Comic not found or not available.")
        return value


class ComicLikeSerializer(ComicInteractionValidationMixin, serializers.ModelSerializer):
    comic_id = serializers.CharField(required=True)

    class Meta:
        model = ComicLikeLink
        fields = ['comic_id']

    def create(self, validated_data):
        comic_id = validated_data['comic_id']
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))
        
        # We allow IntegrityError to bubble up to the view where it is caught and returned as 409
        like = ComicLikeLink.objects.create(
            comic_id=comic_id,
            user_id=user_id,
            created_by_id=user_id,
            created_at=timezone.now()
        )
        return like


class ComicBookmarkSerializer(ComicInteractionValidationMixin, serializers.ModelSerializer):
    comic_id = serializers.CharField(required=True)

    class Meta:
        model = ComicBookmarkLink
        fields = ['comic_id']

    def create(self, validated_data):
        comic_id = validated_data['comic_id']
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))
        
        bookmark = ComicBookmarkLink.objects.create(
            comic_id=comic_id,
            user_id=user_id,
            created_by_id=user_id,
            created_at=timezone.now()
        )
        return bookmark


class ComicReadingProgressSerializer(ComicInteractionValidationMixin, serializers.ModelSerializer):
    comic_id = serializers.CharField(required=True)
    last_chapter_id = serializers.CharField(required=False, allow_null=True)
    last_page_number = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = ComicReadingProgress
        fields = ['comic_id', 'last_chapter_id', 'last_page_number']

    def validate(self, attrs):
        # We already validated comic_id in validate_comic_id via the mixin
        comic_id = attrs.get('comic_id')
        last_chapter_id = attrs.get('last_chapter_id')
        last_page_number = attrs.get('last_page_number')

        if last_chapter_id:
            # Verify chapter belongs to this comic and is published/active
            chapter = Chapter.objects.filter(
                id=last_chapter_id,
                comic_id=comic_id,
                status=Comic.Status.PUBLISHED,
                deleted_at__isnull=True
            ).first()
            if not chapter:
                raise serializers.ValidationError({"last_chapter_id": "Chapter not found, not published, or does not belong to this comic."})
            
            if last_page_number is not None:
                # Verify page exists in that chapter and is active
                page_exists = chapter.pages.filter(
                    page_number=last_page_number,
                    deleted_at__isnull=True
                ).exists()
                if not page_exists:
                    raise serializers.ValidationError({"last_page_number": "Page not found in this chapter."})
        elif last_page_number is not None:
            raise serializers.ValidationError({"last_page_number": "Cannot provide page number without chapter."})

        return attrs

    def create(self, validated_data):
        comic_id = validated_data['comic_id']
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))
        last_chapter_id = validated_data.get('last_chapter_id')
        last_page_number = validated_data.get('last_page_number')
        now = timezone.now()
        
        try:
            with transaction.atomic():
                progress = ComicReadingProgress.objects.create(
                    user_id=user_id,
                    comic_id=comic_id,
                    last_chapter_id=last_chapter_id,
                    last_page_number=last_page_number,
                    updated_at=now,
                    created_at=now
                )
        except IntegrityError:
            progress = ComicReadingProgress.objects.get(user_id=user_id, comic_id=comic_id)
            progress.last_chapter_id = last_chapter_id
            progress.last_page_number = last_page_number
            progress.updated_at = now
            progress.save(update_fields=['last_chapter_id', 'last_page_number', 'updated_at'])
            
        return progress


class PaginatedBookmarkSerializer(serializers.ModelSerializer):
    comic_id = serializers.CharField(source='comic.id')
    title = serializers.CharField(source='comic.title')
    slug = serializers.CharField(source='comic.slug')
    cover_image_key = serializers.CharField(source='comic.cover_image_key')
    bookmarked_at = serializers.DateTimeField(source='created_at')
    
    class Meta:
        model = ComicBookmarkLink
        fields = ['id', 'comic_id', 'title', 'slug', 'cover_image_key', 'bookmarked_at']
        

class PaginatedProgressSerializer(serializers.ModelSerializer):
    comic_id = serializers.CharField(source='comic.id')
    title = serializers.CharField(source='comic.title')
    slug = serializers.CharField(source='comic.slug')
    cover_image_key = serializers.CharField(source='comic.cover_image_key')
    last_read_at = serializers.DateTimeField(source='updated_at')
    
    class Meta:
        model = ComicReadingProgress
        fields = [
            'id', 'comic_id', 'title', 'slug', 'cover_image_key', 
            'last_chapter_id', 'last_page_number', 'last_read_at'
        ]
