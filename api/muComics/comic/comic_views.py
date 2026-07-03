"""
Comic CRUD views.

Endpoints:
  GET    /muComics/comics/                      → list (paginated, search, filter, sort)
  POST   /muComics/comics/                      → create
  GET    /muComics/comics/<comic_id>/            → detail
  PATCH  /muComics/comics/<comic_id>/            → partial update (creator or editor)
  DELETE /muComics/comics/<comic_id>/            → soft delete (creator only)
  POST   /muComics/comics/<comic_id>/publish/    → draft → published (creator only)
  POST   /muComics/comics/<comic_id>/archive/    → published/draft → archived (creator only)
"""

from django.utils import timezone
from django.db.models import Q

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s
from rest_framework.views import APIView

from db.comic import Comic, ComicContributorLink
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils

from .serializers import (
    ComicListItemSerializer,
    ComicDetailSerializer,
    ComicWriteSerializer,
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_active_comics():
    """Base queryset: exclude soft-deleted rows."""
    return Comic.objects.filter(deleted_at__isnull=True)


def can_edit_comic(user_id, comic):
    """
    True if the user is the comic's creator OR has been explicitly assigned
    as an 'editor' contributor on that comic by the creator.
    """
    if comic.created_by_id == user_id:
        return True
    return ComicContributorLink.objects.filter(
        comic=comic,
        user_id=user_id,
        contributor_type=ComicContributorLink.ContributorType.EDITOR,
    ).exists()


# ─────────────────────────────────────────────────────────────────────────────
# COMIC LIST + CREATE
# ─────────────────────────────────────────────────────────────────────────────

class ComicListCreateView(APIView):
    """
    GET  /muComics/comics/  → paginated list with search, status filter, sort
    POST /muComics/comics/  → create a new comic (any authenticated user)
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['muComics'],
        description="List all active (non-deleted) comics. Supports search by title, status filter, and sort by created_at or title.",
        responses={200: ComicListItemSerializer(many=True)},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        queryset = _get_active_comics()

        # Optional status filter: ?status=draft|published|archived
        if status_filter := request.query_params.get('status'):
            if status_filter not in Comic.Status.values:
                return CustomResponse(
                    general_message=f'Invalid status. Allowed: {", ".join(Comic.Status.values)}.'
                ).get_failure_response()
            queryset = queryset.filter(status=status_filter)

        paginated = CommonUtils.get_paginated_queryset(
            queryset.select_related('created_by'),
            request,
            search_fields=['title'],
            sort_fields={
                'created_at': 'created_at',
                'title':      'title',
            },
        )

        serializer = ComicListItemSerializer(
            paginated['queryset'], many=True,
            context={'user_id': user_id},
        )
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )

    @extend_schema(
        tags=['muComics'],
        description="Create a new comic. Any authenticated user may create a comic. Returns the full comic detail on success.",
        request=ComicWriteSerializer,
        responses={200: ComicDetailSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        serializer = ComicWriteSerializer(
            data=request.data,
            context={'user_id': user_id},
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()

        comic = serializer.save()

        return CustomResponse(
            general_message=f'Comic "{comic.title}" created successfully.',
            response=ComicDetailSerializer(
                comic, context={'user_id': user_id}
            ).data,
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# COMIC DETAIL — GET / PATCH / DELETE
# ─────────────────────────────────────────────────────────────────────────────

class ComicDetailView(APIView):
    """
    GET    /muComics/comics/<comic_id>/   → full detail
    PATCH  /muComics/comics/<comic_id>/   → partial update (creator or assigned editor)
    DELETE /muComics/comics/<comic_id>/   → soft delete (creator only)
    """
    authentication_classes = [CustomizePermission]

    def _get_comic_or_error(self, comic_id):
        """Fetch an active comic or return an error string."""
        comic = _get_active_comics().filter(id=comic_id).first()
        if not comic:
            return None, 'Comic not found.'
        return comic, None

    @extend_schema(
        tags=['muComics'],
        description="Retrieve full detail for a single active comic, including contributors and genres.",
        responses={200: ComicDetailSerializer},
    )
    def get(self, request, comic_id):
        user_id = JWTUtils.fetch_user_id(request)
        comic, error = self._get_comic_or_error(comic_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response()

        return CustomResponse(
            general_message=f'Comic "{comic.title}" retrieved successfully.',
            response=ComicDetailSerializer(
                comic, context={'user_id': user_id}
            ).data,
        ).get_success_response()

    @extend_schema(
        tags=['muComics'],
        description="Partially update a comic's title, description, or cover image. Only the creator or an assigned editor contributor may edit. Archived comics cannot be edited.",
        request=ComicWriteSerializer,
        responses={200: ComicDetailSerializer},
    )
    def patch(self, request, comic_id):
        user_id = JWTUtils.fetch_user_id(request)
        comic, error = self._get_comic_or_error(comic_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response()

        # Permission: creator or assigned editor
        if not can_edit_comic(user_id, comic):
            return CustomResponse(
                general_message='You do not have permission to edit this comic.'
            ).get_unauthorized_response()

        # Archived comics cannot be edited
        if comic.status == Comic.Status.ARCHIVED:
            return CustomResponse(
                general_message='Archived comics cannot be edited.'
            ).get_failure_response()

        serializer = ComicWriteSerializer(
            comic, data=request.data,
            partial=True,
            context={'user_id': user_id},
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()

        comic = serializer.save()

        return CustomResponse(
            general_message=f'Comic "{comic.title}" updated successfully.',
            response=ComicDetailSerializer(
                comic, context={'user_id': user_id}
            ).data,
        ).get_success_response()

    @extend_schema(
        tags=['muComics'],
        description="Soft-delete a comic (sets deleted_at). Only the original creator may delete. The comic is hidden from all list/detail responses after deletion.",
        responses={200: inline_serializer(
            name='ComicDeleteResponse',
            fields={'id': s.CharField()},
        )},
    )
    def delete(self, request, comic_id):
        user_id = JWTUtils.fetch_user_id(request)
        comic, error = self._get_comic_or_error(comic_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response()

        # Only the original creator can delete
        if comic.created_by_id != user_id:
            return CustomResponse(
                general_message='Only the comic creator can delete this comic.'
            ).get_unauthorized_response()

        now = timezone.now()
        comic.deleted_at    = now
        comic.deleted_by_id = user_id
        comic.updated_by_id = user_id
        comic.updated_at    = now
        comic.save()

        return CustomResponse(
            general_message=f'Comic "{comic.title}" deleted successfully.',
            response={'id': comic.id},
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# PUBLISH
# ─────────────────────────────────────────────────────────────────────────────

class ComicPublishView(APIView):
    """
    POST /muComics/comics/<comic_id>/publish/
    Transitions a draft comic to published (creator only).

    Workflow:
        draft     → published   ✅
        archived  → ❌  (cannot re-publish archived)
        published → ❌  (already published)
    """
    authentication_classes = [CustomizePermission]

    REQUIRED_FIELDS = ['title', 'description']

    @extend_schema(
        tags=['muComics'],
        description="Publish a draft comic (draft → published). Only the creator may publish. Requires title and description to be present. Archived comics cannot be re-published.",
        responses={200: inline_serializer(
            name='ComicPublishResponse',
            fields={
                'id':     s.CharField(),
                'status': s.CharField(),
            },
        )},
    )
    def post(self, request, comic_id):
        user_id = JWTUtils.fetch_user_id(request)
        comic   = _get_active_comics().filter(id=comic_id).first()

        if not comic:
            return CustomResponse(general_message='Comic not found.').get_failure_response()

        # Only creator can publish
        if comic.created_by_id != user_id:
            return CustomResponse(
                general_message='Only the comic creator can publish this comic.'
            ).get_unauthorized_response()

        if comic.status == Comic.Status.PUBLISHED:
            return CustomResponse(
                general_message='Comic is already published.'
            ).get_failure_response()

        if comic.status == Comic.Status.ARCHIVED:
            return CustomResponse(
                general_message='Archived comics cannot be published. Unarchive it first.'
            ).get_failure_response()

        # Validate required fields are filled before publishing
        missing = [f for f in self.REQUIRED_FIELDS if not getattr(comic, f, None)]
        if missing:
            return CustomResponse(
                general_message=f'Cannot publish: missing required fields: {", ".join(missing)}.'
            ).get_failure_response()

        now = timezone.now()
        comic.status        = Comic.Status.PUBLISHED
        comic.published_at  = now
        comic.updated_by_id = user_id
        comic.updated_at    = now
        comic.save(update_fields=['status', 'published_at', 'updated_by', 'updated_at'])

        return CustomResponse(
            general_message=f'Comic "{comic.title}" published successfully.',
            response={'id': comic.id, 'status': Comic.Status.PUBLISHED},
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# ARCHIVE
# ─────────────────────────────────────────────────────────────────────────────

class ComicArchiveView(APIView):
    """
    POST /muComics/comics/<comic_id>/archive/
    Transitions a draft or published comic to archived (creator only).

    Workflow:
        draft     → archived  ✅
        published → archived  ✅
        archived  → ❌  (already archived)
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['muComics'],
        description="Archive a draft or published comic (draft/published → archived). Only the creator may archive. Already-archived comics are rejected.",
        responses={200: inline_serializer(
            name='ComicArchiveResponse',
            fields={
                'id':     s.CharField(),
                'status': s.CharField(),
            },
        )},
    )
    def post(self, request, comic_id):
        user_id = JWTUtils.fetch_user_id(request)
        comic   = _get_active_comics().filter(id=comic_id).first()

        if not comic:
            return CustomResponse(general_message='Comic not found.').get_failure_response()

        # Only creator can archive
        if comic.created_by_id != user_id:
            return CustomResponse(
                general_message='Only the comic creator can archive this comic.'
            ).get_unauthorized_response()

        if comic.status == Comic.Status.ARCHIVED:
            return CustomResponse(
                general_message='Comic is already archived.'
            ).get_failure_response()

        now = timezone.now()
        comic.status        = Comic.Status.ARCHIVED
        comic.updated_by_id = user_id
        comic.updated_at    = now
        comic.save(update_fields=['status', 'updated_by', 'updated_at'])

        return CustomResponse(
            general_message=f'Comic "{comic.title}" archived successfully.',
            response={'id': comic.id, 'status': Comic.Status.ARCHIVED},
        ).get_success_response()
