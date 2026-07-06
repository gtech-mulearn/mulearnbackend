"""
MuComics Comment views — public comment CRUD (Endpoints 1-6).

Endpoints:
  GET    /muComics/comments/comic/<comic_id>/          → list comic comments
  GET    /muComics/comments/chapter/<chapter_id>/       → list chapter comments
  POST   /muComics/comments/comic/<comic_id>/          → create comic comment
  POST   /muComics/comments/chapter/<chapter_id>/       → create chapter comment
  PATCH  /muComics/comments/<comment_id>/               → edit own comment
  DELETE /muComics/comments/<comment_id>/               → soft-delete own comment
"""
import uuid

from django.db import connection
from django.db.models import Q
from django.utils import timezone
from rest_framework.views import APIView

from db.comic import Comic
from db.comic_comment import ComicComment
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils

from .comment_serializers import (
    CommentListSerializer,
    CommentCreateSerializer,
    CommentUpdateSerializer,
    CommentUserSerializer,
)


def _get_user_id_or_none(request):
    """Safely extract user_id from JWT; returns None if unauthenticated."""
    try:
        return JWTUtils.fetch_user_id(request)
    except Exception:
        return None


def _chapter_exists(chapter_id):
    """Check if a chapter exists and return its comic_id."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT comic_id FROM chapter WHERE id = %s LIMIT 1", [chapter_id]
        )
        row = cursor.fetchone()
        return row[0] if row else None


def _increment_comment_count(comic_id):
    """Atomically increment comic.comment_count by 1."""
    Comic.objects.filter(id=comic_id).update(
        comment_count=models.F('comment_count') + 1
    )


def _decrement_comment_count(comic_id):
    """Atomically decrement comic.comment_count by 1 (min 0)."""
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE comic SET comment_count = GREATEST(comment_count - 1, 0) WHERE id = %s",
            [comic_id],
        )


# Need to import models for F expression
from django.db import models


class ComicCommentListCreateAPI(APIView):
    """
    GET  /comments/comic/<comic_id>/  — list top-level comments with replies
    POST /comments/comic/<comic_id>/  — create a comment (top-level or reply)
    """

    def get(self, request, comic_id):
        comic = Comic.objects.filter(id=comic_id, deleted_at__isnull=True).first()
        if not comic:
            return CustomResponse(
                general_message="Comic not found"
            ).get_failure_response(status_code=404, http_status_code=404)

        user_id = _get_user_id_or_none(request)

        # Get top-level comments (parent_id is NULL)
        # Include: active comments OR soft-deleted comments that have active replies
        top_level = ComicComment.objects.filter(
            comic_id=comic_id,
            parent__isnull=True,
        ).select_related('user')

        # Filter out soft-deleted comments with no active replies
        visible_ids = []
        for comment in top_level:
            if not comment.is_deleted:
                visible_ids.append(comment.id)
            else:
                has_active_replies = comment.replies.filter(deleted_at__isnull=True).exists()
                if has_active_replies:
                    visible_ids.append(comment.id)

        queryset = ComicComment.objects.filter(
            id__in=visible_ids
        ).select_related('user').order_by('-created_at')

        paginated = CommonUtils.get_paginated_queryset(
            queryset,
            request,
            search_fields=['message'],
            sort_fields={'created_at': 'created_at'},
        )

        serializer = CommentListSerializer(
            paginated['queryset'], many=True,
            context={'user_id': user_id},
        )

        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )

    def post(self, request, comic_id):
        try:
            JWTUtils.is_jwt_authenticated(request)
        except Exception:
            return CustomResponse(
                general_message="Invalid token header"
            ).get_failure_response(status_code=1000, http_status_code=401)

        user_id = JWTUtils.fetch_user_id(request)

        comic = Comic.objects.filter(id=comic_id, deleted_at__isnull=True).first()
        if not comic:
            return CustomResponse(
                general_message="Comic not found"
            ).get_failure_response(status_code=404, http_status_code=404)

        serializer = CommentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                message=serializer.errors
            ).get_failure_response()

        message = serializer.validated_data['message']
        parent_id = serializer.validated_data.get('parent_id')

        # Validate parent_id
        if parent_id:
            try:
                parent = ComicComment.objects.get(id=parent_id)
            except ComicComment.DoesNotExist:
                return CustomResponse(
                    message={"parent_id": ["Parent comment not found"]}
                ).get_failure_response()

            if parent.parent_id is not None:
                return CustomResponse(
                    message={"parent_id": ["Replies can only be made to top-level comments"]}
                ).get_failure_response()

            if parent.comic_id != comic_id:
                return CustomResponse(
                    message={"parent_id": ["Parent comment does not belong to this comic"]}
                ).get_failure_response()

            if parent.is_deleted:
                return CustomResponse(
                    message={"parent_id": ["Cannot reply to a deleted comment"]}
                ).get_failure_response()

        now = timezone.now()
        comment = ComicComment.objects.create(
            id=str(uuid.uuid4()),
            comic_id=comic_id,
            chapter_id=None,
            parent_id=parent_id,
            user_id=user_id,
            message=message,
            updated_by_id=user_id,
            updated_at=now,
            created_by_id=user_id,
            created_at=now,
        )

        _increment_comment_count(comic_id)

        from db.user import User
        user = User.objects.get(id=user_id)

        return CustomResponse(
            general_message="Comment created successfully",
            response={
                "id": comment.id,
                "comic_id": comment.comic_id,
                "chapter_id": comment.chapter_id,
                "parent_id": comment.parent_id,
                "user": CommentUserSerializer(user).data,
                "message": comment.message,
                "is_edited": False,
                "created_at": comment.created_at,
                "updated_at": comment.updated_at,
            },
        ).get_success_response()


class ChapterCommentListCreateAPI(APIView):
    """
    GET  /comments/chapter/<chapter_id>/  — list chapter comments
    POST /comments/chapter/<chapter_id>/  — create chapter comment
    """

    def get(self, request, chapter_id):
        comic_id = _chapter_exists(chapter_id)
        if not comic_id:
            return CustomResponse(
                general_message="Chapter not found"
            ).get_failure_response(status_code=404, http_status_code=404)

        user_id = _get_user_id_or_none(request)

        top_level = ComicComment.objects.filter(
            chapter_id=chapter_id,
            parent__isnull=True,
        ).select_related('user')

        visible_ids = []
        for comment in top_level:
            if not comment.is_deleted:
                visible_ids.append(comment.id)
            else:
                if comment.replies.filter(deleted_at__isnull=True).exists():
                    visible_ids.append(comment.id)

        queryset = ComicComment.objects.filter(
            id__in=visible_ids
        ).select_related('user').order_by('-created_at')

        paginated = CommonUtils.get_paginated_queryset(
            queryset,
            request,
            search_fields=['message'],
            sort_fields={'created_at': 'created_at'},
        )

        serializer = CommentListSerializer(
            paginated['queryset'], many=True,
            context={'user_id': user_id},
        )

        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )

    def post(self, request, chapter_id):
        try:
            JWTUtils.is_jwt_authenticated(request)
        except Exception:
            return CustomResponse(
                general_message="Invalid token header"
            ).get_failure_response(status_code=1000, http_status_code=401)

        user_id = JWTUtils.fetch_user_id(request)

        comic_id = _chapter_exists(chapter_id)
        if not comic_id:
            return CustomResponse(
                general_message="Chapter not found"
            ).get_failure_response(status_code=404, http_status_code=404)

        serializer = CommentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                message=serializer.errors
            ).get_failure_response()

        message = serializer.validated_data['message']
        parent_id = serializer.validated_data.get('parent_id')

        if parent_id:
            try:
                parent = ComicComment.objects.get(id=parent_id)
            except ComicComment.DoesNotExist:
                return CustomResponse(
                    message={"parent_id": ["Parent comment not found"]}
                ).get_failure_response()

            if parent.parent_id is not None:
                return CustomResponse(
                    message={"parent_id": ["Replies can only be made to top-level comments"]}
                ).get_failure_response()

            if parent.chapter_id != chapter_id:
                return CustomResponse(
                    message={"parent_id": ["Parent comment does not belong to this chapter"]}
                ).get_failure_response()

            if parent.is_deleted:
                return CustomResponse(
                    message={"parent_id": ["Cannot reply to a deleted comment"]}
                ).get_failure_response()

        now = timezone.now()
        comment = ComicComment.objects.create(
            id=str(uuid.uuid4()),
            comic_id=comic_id,
            chapter_id=chapter_id,
            parent_id=parent_id,
            user_id=user_id,
            message=message,
            updated_by_id=user_id,
            updated_at=now,
            created_by_id=user_id,
            created_at=now,
        )

        _increment_comment_count(comic_id)

        from db.user import User
        user = User.objects.get(id=user_id)

        return CustomResponse(
            general_message="Comment created successfully",
            response={
                "id": comment.id,
                "comic_id": comment.comic_id,
                "chapter_id": comment.chapter_id,
                "parent_id": comment.parent_id,
                "user": CommentUserSerializer(user).data,
                "message": comment.message,
                "is_edited": False,
                "created_at": comment.created_at,
                "updated_at": comment.updated_at,
            },
        ).get_success_response()


class CommentDetailAPI(APIView):
    """
    PATCH  /comments/<comment_id>/  — edit own comment
    DELETE /comments/<comment_id>/  — soft-delete own comment
    """
    permission_classes = [CustomizePermission]

    def patch(self, request, comment_id):
        user_id = JWTUtils.fetch_user_id(request)

        try:
            comment = ComicComment.objects.get(id=comment_id)
        except ComicComment.DoesNotExist:
            return CustomResponse(
                general_message="Comment not found"
            ).get_failure_response(status_code=404, http_status_code=404)

        if comment.is_deleted:
            return CustomResponse(
                general_message="Cannot edit a deleted comment"
            ).get_failure_response()

        if comment.user_id != user_id:
            return CustomResponse(
                general_message="You can only edit your own comments"
            ).get_failure_response(status_code=403, http_status_code=403)

        serializer = CommentUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                message=serializer.errors
            ).get_failure_response()

        now = timezone.now()
        comment.message = serializer.validated_data['message']
        comment.updated_by_id = user_id
        comment.updated_at = now
        comment.save()

        return CustomResponse(
            general_message="Comment updated successfully",
            response={
                "id": comment.id,
                "message": comment.message,
                "is_edited": True,
                "updated_at": comment.updated_at,
            },
        ).get_success_response()

    def delete(self, request, comment_id):
        user_id = JWTUtils.fetch_user_id(request)

        try:
            comment = ComicComment.objects.get(id=comment_id)
        except ComicComment.DoesNotExist:
            return CustomResponse(
                general_message="Comment not found"
            ).get_failure_response(status_code=404, http_status_code=404)

        if comment.is_deleted:
            return CustomResponse(
                general_message="Comment has already been deleted"
            ).get_failure_response()

        if comment.user_id != user_id:
            return CustomResponse(
                general_message="You can only delete your own comments"
            ).get_failure_response(status_code=403, http_status_code=403)

        now = timezone.now()
        comment.deleted_at = now
        comment.deleted_by_id = user_id
        comment.updated_at = now
        comment.save()

        _decrement_comment_count(comment.comic_id)

        return CustomResponse(
            general_message="Comment deleted successfully"
        ).get_success_response()
