import os
import uuid

from decouple import config as decouple_config
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from django.db import transaction
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s

from db.comic import Comic, Chapter, ChapterPage
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils

from api.muComics.comic.comic_views import can_edit_comic
from .serializers import (
    ChapterListSerializer,
    ChapterDetailSerializer,
    ChapterWriteSerializer,
    ChapterPageSerializer,
)


# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER LIST + CREATE
# ─────────────────────────────────────────────────────────────────────────────

class ChapterListCreateView(APIView):
    """
    GET  /muComics/chapters/?comic_id=<comic_id>  → List chapters of a comic
    POST /muComics/chapters/                      → Create a chapter
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['muComics - Chapters'],
        description="List all active (non-deleted) chapters for a comic. Supports status filter and search by title.",
        responses={200: ChapterListSerializer(many=True)},
    )
    def get(self, request):
        comic_id = request.query_params.get('comic_id')
        if not comic_id:
            return CustomResponse(
                general_message='comic_id query parameter is required.'
            ).get_failure_response()

        # Check if comic exists and is active
        comic = Comic.objects.filter(id=comic_id, deleted_at__isnull=True).first()
        if not comic:
            return CustomResponse(
                general_message='Comic not found.'
            ).get_failure_response(status_code=404, http_status_code=404)

        queryset = Chapter.objects.filter(comic_id=comic_id, deleted_at__isnull=True)

        # Optional status filter: ?status=draft|published|archived
        if status_filter := request.query_params.get('status'):
            if status_filter not in Comic.Status.values:
                return CustomResponse(
                    general_message=f'Invalid status. Allowed: {", ".join(Comic.Status.values)}.'
                ).get_failure_response()
            queryset = queryset.filter(status=status_filter)

        paginated = CommonUtils.get_paginated_queryset(
            queryset,
            request,
            search_fields=['title'],
            sort_fields={
                'chapter_number': 'chapter_number',
                'created_at': 'created_at',
            },
        )

        serializer = ChapterListSerializer(paginated['queryset'], many=True)
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )

    @extend_schema(
        tags=['muComics - Chapters'],
        description="Create a new chapter inside a comic. Only creator or editors of the comic can create.",
        request=ChapterWriteSerializer,
        responses={200: ChapterDetailSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        comic_id = request.data.get('comic')
        
        if not comic_id:
            return CustomResponse(
                general_message='comic is required.'
            ).get_failure_response()

        comic = Comic.objects.filter(id=comic_id, deleted_at__isnull=True).first()
        if not comic:
            return CustomResponse(
                general_message='Comic not found.'
            ).get_failure_response(status_code=404, http_status_code=404)

        # Permission: creator or assigned editor of the comic
        if not can_edit_comic(user_id, comic):
            return CustomResponse(
                general_message='You do not have permission to add a chapter to this comic.'
            ).get_unauthorized_response()

        serializer = ChapterWriteSerializer(
            data=request.data,
            context={'user_id': user_id},
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()

        chapter = serializer.save()
        return CustomResponse(
            general_message=f'Chapter "{chapter.title}" created successfully.',
            response=ChapterDetailSerializer(chapter).data,
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER DETAIL — GET / PATCH / DELETE
# ─────────────────────────────────────────────────────────────────────────────

class ChapterDetailView(APIView):
    """
    GET    /muComics/chapters/<chapter_id>/   → detail
    PATCH  /muComics/chapters/<chapter_id>/   → update
    DELETE /muComics/chapters/<chapter_id>/   → soft delete (comic creator only)
    """
    authentication_classes = [CustomizePermission]

    def _get_chapter_or_error(self, chapter_id):
        chapter = Chapter.objects.filter(id=chapter_id, deleted_at__isnull=True).select_related('comic').first()
        if not chapter:
            return None, 'Chapter not found.'
        return chapter, None

    @extend_schema(
        tags=['muComics - Chapters'],
        description="Retrieve full detail of a chapter including pages.",
        responses={200: ChapterDetailSerializer},
    )
    def get(self, request, chapter_id):
        chapter, error = self._get_chapter_or_error(chapter_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response(status_code=404, http_status_code=404)

        return CustomResponse(
            general_message=f'Chapter "{chapter.title}" retrieved successfully.',
            response=ChapterDetailSerializer(chapter).data,
        ).get_success_response()

    @extend_schema(
        tags=['muComics - Chapters'],
        description="Update chapter details. Requires comic creator or editor permissions. Archived chapters cannot be edited.",
        request=ChapterWriteSerializer,
        responses={200: ChapterDetailSerializer},
    )
    def patch(self, request, chapter_id):
        user_id = JWTUtils.fetch_user_id(request)
        chapter, error = self._get_chapter_or_error(chapter_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response(status_code=404, http_status_code=404)

        # Permission: creator or assigned editor of the comic
        if not can_edit_comic(user_id, chapter.comic):
            return CustomResponse(
                general_message='You do not have permission to edit this chapter.'
            ).get_unauthorized_response()

        # Archived chapters cannot be edited
        if chapter.status == Comic.Status.ARCHIVED:
            return CustomResponse(
                general_message='Archived chapters cannot be edited.'
            ).get_failure_response()

        serializer = ChapterWriteSerializer(
            chapter, data=request.data,
            partial=True,
            context={'user_id': user_id},
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()

        chapter = serializer.save()
        return CustomResponse(
            general_message=f'Chapter "{chapter.title}" updated successfully.',
            response=ChapterDetailSerializer(chapter).data,
        ).get_success_response()

    @extend_schema(
        tags=['muComics - Chapters'],
        description="Soft delete a chapter. Only the comic creator can delete a chapter.",
        responses={200: inline_serializer(
            name='ChapterDeleteResponse',
            fields={'id': s.CharField()},
        )},
    )
    def delete(self, request, chapter_id):
        user_id = JWTUtils.fetch_user_id(request)
        chapter, error = self._get_chapter_or_error(chapter_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response(status_code=404, http_status_code=404)

        # Only the comic creator can delete a chapter
        if chapter.comic.created_by_id != user_id:
            return CustomResponse(
                general_message='Only the comic creator can delete this chapter.'
            ).get_unauthorized_response()

        now = timezone.now()
        with transaction.atomic():
            chapter.deleted_at = now
            chapter.deleted_by_id = user_id
            chapter.updated_by_id = user_id
            chapter.updated_at = now
            chapter.save(update_fields=['deleted_at', 'deleted_by', 'updated_by', 'updated_at'])

            # Soft delete all linked pages too
            ChapterPage.objects.filter(chapter=chapter, deleted_at__isnull=True).update(
                deleted_at=now,
                deleted_by_id=user_id,
                updated_by_id=user_id,
                updated_at=now
            )

        return CustomResponse(
            general_message=f'Chapter "{chapter.title}" deleted successfully.',
            response={'id': chapter.id},
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER STATUS ACTIONS (PUBLISH / ARCHIVE)
# ─────────────────────────────────────────────────────────────────────────────

class ChapterPublishView(APIView):
    """
    POST /muComics/chapters/<chapter_id>/publish/  → Transition chapter status draft → published
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['muComics - Chapters'],
        description="Publish a chapter. Comic creator only.",
        responses={200: inline_serializer(
            name='ChapterPublishResponse',
            fields={'id': s.CharField(), 'status': s.CharField()},
        )},
    )
    def post(self, request, chapter_id):
        user_id = JWTUtils.fetch_user_id(request)
        chapter = Chapter.objects.filter(id=chapter_id, deleted_at__isnull=True).select_related('comic').first()
        if not chapter:
            return CustomResponse(general_message='Chapter not found.').get_failure_response(status_code=404, http_status_code=404)

        # Only comic creator can publish
        if chapter.comic.created_by_id != user_id:
            return CustomResponse(
                general_message='Only the comic creator can publish this chapter.'
            ).get_unauthorized_response()

        if chapter.status == Comic.Status.PUBLISHED:
            return CustomResponse(general_message='Chapter is already published.').get_failure_response()

        if chapter.status == Comic.Status.ARCHIVED:
            return CustomResponse(general_message='Archived chapters cannot be published.').get_failure_response()

        now = timezone.now()
        chapter.status = Comic.Status.PUBLISHED
        chapter.published_at = now
        chapter.updated_by_id = user_id
        chapter.updated_at = now
        chapter.save(update_fields=['status', 'published_at', 'updated_by', 'updated_at'])

        return CustomResponse(
            general_message=f'Chapter "{chapter.title}" published successfully.',
            response={'id': chapter.id, 'status': Comic.Status.PUBLISHED},
        ).get_success_response()


class ChapterArchiveView(APIView):
    """
    POST /muComics/chapters/<chapter_id>/archive/  → Transition chapter status published/draft → archived
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['muComics - Chapters'],
        description="Archive a chapter. Comic creator only.",
        responses={200: inline_serializer(
            name='ChapterArchiveResponse',
            fields={'id': s.CharField(), 'status': s.CharField()},
        )},
    )
    def post(self, request, chapter_id):
        user_id = JWTUtils.fetch_user_id(request)
        chapter = Chapter.objects.filter(id=chapter_id, deleted_at__isnull=True).select_related('comic').first()
        if not chapter:
            return CustomResponse(general_message='Chapter not found.').get_failure_response(status_code=404, http_status_code=404)

        # Only comic creator can archive
        if chapter.comic.created_by_id != user_id:
            return CustomResponse(
                general_message='Only the comic creator can archive this chapter.'
            ).get_unauthorized_response()

        if chapter.status == Comic.Status.ARCHIVED:
            return CustomResponse(general_message='Chapter is already archived.').get_failure_response()

        now = timezone.now()
        chapter.status = Comic.Status.ARCHIVED
        chapter.updated_by_id = user_id
        chapter.updated_at = now
        chapter.save(update_fields=['status', 'updated_by', 'updated_at'])

        return CustomResponse(
            general_message=f'Chapter "{chapter.title}" archived successfully.',
            response={'id': chapter.id, 'status': Comic.Status.ARCHIVED},
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE LIST + ADD (CREATE)
# ─────────────────────────────────────────────────────────────────────────────

class ChapterPageListCreateAPI(APIView):
    """
    GET  /muComics/chapters/<chapter_id>/pages/  → List pages of a chapter
    POST /muComics/chapters/<chapter_id>/pages/  → Add a single page to a chapter
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['muComics - Pages'],
        description="List all active pages of a chapter, ordered by page number.",
        responses={200: ChapterPageSerializer(many=True)},
    )
    def get(self, request, chapter_id):
        chapter = Chapter.objects.filter(id=chapter_id, deleted_at__isnull=True).first()
        if not chapter:
            return CustomResponse(general_message='Chapter not found.').get_failure_response(status_code=404, http_status_code=404)

        pages = ChapterPage.objects.filter(chapter_id=chapter_id, deleted_at__isnull=True).order_by('page_number')
        serializer = ChapterPageSerializer(pages, many=True)
        return CustomResponse(
            general_message='Pages retrieved successfully.',
            response=serializer.data,
        ).get_success_response()

    @extend_schema(
        tags=['muComics - Pages'],
        description="Add a single page to a chapter. Comic creators or editors only.",
        request=ChapterPageSerializer,
        responses={200: ChapterPageSerializer},
    )
    def post(self, request, chapter_id):
        user_id = JWTUtils.fetch_user_id(request)
        chapter = Chapter.objects.filter(id=chapter_id, deleted_at__isnull=True).select_related('comic').first()
        if not chapter:
            return CustomResponse(general_message='Chapter not found.').get_failure_response(status_code=404, http_status_code=404)

        # Permission: creator or assigned editor of the comic
        if not can_edit_comic(user_id, chapter.comic):
            return CustomResponse(
                general_message='You do not have permission to add a page to this chapter.'
            ).get_unauthorized_response()

        # Inject the chapter into request data
        data = request.data.copy()
        data['chapter'] = chapter_id

        serializer = ChapterPageSerializer(data=data)
        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()

        now = timezone.now()
        page = serializer.save(
            id=str(uuid.uuid4()),
            created_by_id=user_id,
            updated_by_id=user_id,
            created_at=now,
            updated_at=now,
        )

        return CustomResponse(
            general_message='Page added successfully.',
            response=ChapterPageSerializer(page).data,
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE DETAIL (UPDATE / DELETE)
# ─────────────────────────────────────────────────────────────────────────────

class ChapterPageDetailAPI(APIView):
    """
    PATCH  /muComics/pages/<page_id>/   → Update page details
    DELETE /muComics/pages/<page_id>/   → Delete page (soft delete)
    """
    authentication_classes = [CustomizePermission]

    def _get_page_or_error(self, page_id):
        page = ChapterPage.objects.filter(id=page_id, deleted_at__isnull=True).select_related('chapter__comic').first()
        if not page:
            return None, 'Page not found.'
        return page, None

    @extend_schema(
        tags=['muComics - Pages'],
        description="Update page information (e.g. page_number or image_key). Comic creators or editors only.",
        request=ChapterPageSerializer,
        responses={200: ChapterPageSerializer},
    )
    def patch(self, request, page_id):
        user_id = JWTUtils.fetch_user_id(request)
        page, error = self._get_page_or_error(page_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response(status_code=404, http_status_code=404)

        # Permission: creator or assigned editor of the comic
        if not can_edit_comic(user_id, page.chapter.comic):
            return CustomResponse(
                general_message='You do not have permission to update this page.'
            ).get_unauthorized_response()

        serializer = ChapterPageSerializer(
            page, data=request.data,
            partial=True,
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()

        now = timezone.now()
        page = serializer.save(
            updated_by_id=user_id,
            updated_at=now,
        )

        return CustomResponse(
            general_message='Page updated successfully.',
            response=ChapterPageSerializer(page).data,
        ).get_success_response()

    @extend_schema(
        tags=['muComics - Pages'],
        description="Delete a page (soft delete). Comic creators or editors only.",
        responses={200: inline_serializer(
            name='PageDeleteResponse',
            fields={'id': s.CharField()},
        )},
    )
    def delete(self, request, page_id):
        user_id = JWTUtils.fetch_user_id(request)
        page, error = self._get_page_or_error(page_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response(status_code=404, http_status_code=404)

        # Permission: creator or assigned editor of the comic
        if not can_edit_comic(user_id, page.chapter.comic):
            return CustomResponse(
                general_message='You do not have permission to delete this page.'
            ).get_unauthorized_response()

        now = timezone.now()
        page.deleted_at = now
        page.deleted_by_id = user_id
        page.updated_by_id = user_id
        page.updated_at = now
        page.save(update_fields=['deleted_at', 'deleted_by', 'updated_by', 'updated_at'])

        return CustomResponse(
            general_message='Page deleted successfully.',
            response={'id': page.id},
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE REORDER (BULK UPDATE)
# ─────────────────────────────────────────────────────────────────────────────

class ChapterPageReorderAPI(APIView):
    """
    POST /muComics/chapters/<chapter_id>/pages/reorder/  → Bulk update page order
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['muComics - Pages'],
        description="Bulk reorder page numbers in a chapter. Comic creators or editors only.",
        request=inline_serializer(
            name='PageReorderRequest',
            fields={
                'page_orders': s.ListField(
                    child=inline_serializer(
                        name='PageOrderItem',
                        fields={
                            'id': s.CharField(),
                            'page_number': s.IntegerField(),
                        }
                    )
                )
            }
        ),
        responses={200: inline_serializer(
            name='PageReorderResponse',
            fields={'success': s.BooleanField()},
        )},
    )
    def post(self, request, chapter_id):
        user_id = JWTUtils.fetch_user_id(request)
        chapter = Chapter.objects.filter(id=chapter_id, deleted_at__isnull=True).select_related('comic').first()
        if not chapter:
            return CustomResponse(general_message='Chapter not found.').get_failure_response(status_code=404, http_status_code=404)

        # Permission: creator or assigned editor of the comic
        if not can_edit_comic(user_id, chapter.comic):
            return CustomResponse(
                general_message='You do not have permission to reorder pages.'
            ).get_unauthorized_response()

        page_orders = request.data.get('page_orders', [])
        if not isinstance(page_orders, list) or not page_orders:
            return CustomResponse(
                general_message='page_orders must be a non-empty list of page ordering objects.'
            ).get_failure_response()

        # Validate duplicate page numbers or duplicate IDs in request
        for item in page_orders:
            if not isinstance(item, dict) or 'id' not in item or 'page_number' not in item:
                return CustomResponse(
                    general_message='Each page order item must be an object containing both "id" and "page_number".'
                ).get_failure_response()

        ids = [item['id'] for item in page_orders]
        numbers = [item['page_number'] for item in page_orders]


        if len(ids) != len(set(ids)):
            return CustomResponse(general_message='Duplicate page IDs in request.').get_failure_response()
        if len(numbers) != len(set(numbers)):
            return CustomResponse(general_message='Duplicate page numbers in request.').get_failure_response()

        # Check positive page numbers
        if any(num < 1 for num in numbers):
            return CustomResponse(general_message='Page numbers must be positive integers starting from 1.').get_failure_response()

        # Load all pages in chapter to verify IDs belong to this chapter
        pages_qs = ChapterPage.objects.filter(chapter_id=chapter_id, deleted_at__isnull=True)
        pages_dict = {str(page.id): page for page in pages_qs}

        # Verify all input IDs belong to the chapter
        for page_id in ids:
            if page_id not in pages_dict:
                return CustomResponse(
                    general_message=f'Page ID {page_id} does not exist in this chapter.'
                ).get_failure_response(status_code=404, http_status_code=404)

        # Verify all pages in DB are accounted for in the reorder request
        if len(ids) != len(pages_dict):
            return CustomResponse(
                general_message='All active pages in the chapter must be included in the reorder request.'
            ).get_failure_response()

        now = timezone.now()
        with transaction.atomic():
            # Update each page number individually using update_fields
            for item in page_orders:
                page_id = item['id']
                new_num = item['page_number']
                page = pages_dict[page_id]
                page.page_number = new_num
                page.updated_by_id = user_id
                page.updated_at = now
                page.save(update_fields=['page_number', 'updated_by', 'updated_at'])

        return CustomResponse(
            general_message='Pages reordered successfully.',
            response={'success': True},
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD APIS (PRESIGNED UPLOAD URL & REGISTER PAGES)
# ─────────────────────────────────────────────────────────────────────────────

class ChapterUploadURLAPI(APIView):
    """
    POST /muComics/chapters/upload-url/  → Direct file upload (images and PDFs) to local storage.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['muComics - Uploads'],
        description="Upload a media file (Image or PDF) to local storage.",
        request={
            'multipart/form-data': inline_serializer(
                name='ChapterUploadRequest',
                fields={
                    'file': s.FileField(),
                }
            )
        },
        responses={200: inline_serializer(
            name='UploadURLResponse',
            fields={
                'upload_url': s.CharField(),
                'image_key': s.CharField(),
            }
        )},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        file_obj = request.FILES.get('file')

        if file_obj is None:
            return CustomResponse(
                general_message='No file provided.'
            ).get_failure_response()

        content_type = file_obj.content_type or ''
        file_name = file_obj.name or ''
        ext = os.path.splitext(file_name)[1].lower()

        is_image = content_type.startswith("image/") or ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        is_pdf = content_type == "application/pdf" or ext == ".pdf"

        if not (is_image or is_pdf):
            return CustomResponse(
                general_message='Unsupported file type. Only images and PDFs are allowed.'
            ).get_failure_response()

        if is_image:
            if file_obj.size > 5 * 1024 * 1024:
                return CustomResponse(
                    general_message='Image file must be under 5 MB.'
                ).get_failure_response()
            try:
                from PIL import Image
                img = Image.open(file_obj)
                img.verify()
                file_obj.seek(0)
            except Exception:
                return CustomResponse(
                    general_message='Invalid or corrupted image file.'
                ).get_failure_response()

        elif is_pdf:
            if file_obj.size > 20 * 1024 * 1024:
                return CustomResponse(
                    general_message='PDF file must be under 20 MB.'
                ).get_failure_response()

        fs = FileSystemStorage()
        unique_id = uuid.uuid4()
        image_key = f"comics/chapters/{unique_id}{ext}"
        
        fs.save(image_key, file_obj)

        be_domain = decouple_config("BE_DOMAIN_NAME")
        upload_url = f"{be_domain}{fs.url(image_key)}"

        return CustomResponse(
            general_message='File uploaded successfully.',
            response={
                'upload_url': upload_url,
                'image_key': image_key,
            }
        ).get_success_response()


class ChapterRegisterImagesAPI(APIView):
    """
    POST /muComics/chapters/<chapter_id>/pages/register/  → Register uploaded local media paths as chapter pages
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['muComics - Uploads'],
        description="Register multiple uploaded local media paths as sequential pages inside a chapter. Creator/editors only.",
        request=inline_serializer(
            name='RegisterImagesRequest',
            fields={
                'image_keys': s.ListField(child=s.CharField())
            }
        ),
        responses={200: ChapterPageSerializer(many=True)},
    )
    def post(self, request, chapter_id):
        user_id = JWTUtils.fetch_user_id(request)
        chapter = Chapter.objects.filter(id=chapter_id, deleted_at__isnull=True).select_related('comic').first()
        if not chapter:
            return CustomResponse(general_message='Chapter not found.').get_failure_response(status_code=404, http_status_code=404)

        # Permission: creator or assigned editor of the comic
        if not can_edit_comic(user_id, chapter.comic):
            return CustomResponse(
                general_message='You do not have permission to register pages in this chapter.'
            ).get_unauthorized_response()

        image_keys = request.data.get('image_keys', [])
        if not isinstance(image_keys, list) or not image_keys:
            return CustomResponse(
                general_message='image_keys must be a non-empty list of string paths.'
            ).get_failure_response()

        # Validate string image keys
        if not all(isinstance(k, str) and k.strip() for k in image_keys):
            return CustomResponse(
                general_message='Each image key must be a non-empty string.'
            ).get_failure_response()

        now = timezone.now()
        with transaction.atomic():
            # Get the current maximum page number in the chapter
            max_page = ChapterPage.objects.filter(chapter_id=chapter_id, deleted_at__isnull=True).order_by('-page_number').first()
            start_num = max_page.page_number if max_page else 0

            created_pages = []
            for i, image_key in enumerate(image_keys, start=1):
                page = ChapterPage.objects.create(
                    id=str(uuid.uuid4()),
                    chapter=chapter,
                    page_number=start_num + i,
                    image_key=image_key,
                    created_by_id=user_id,
                    updated_by_id=user_id,
                    created_at=now,
                    updated_at=now,
                )
                created_pages.append(page)

        return CustomResponse(
            general_message=f'Registered {len(created_pages)} pages successfully.',
            response=ChapterPageSerializer(created_pages, many=True, context={'request': request}).data,
        ).get_success_response()
