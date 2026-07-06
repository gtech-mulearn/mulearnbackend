"""
MuComics Admin/Moderation views (Endpoints 7-8).
Requires Comic Admin role.
"""
from django.utils import timezone
from django.db import transaction
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from db.comic_comment import ComicComment
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.utils import CommonUtils

from .comment_serializers import AdminCommentListSerializer
from .comment_views import _decrement_comment_count


class AdminCommentListAPI(APIView):
    """
    GET /admin/comments/ — list all comments for moderation (flat list)
    """
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['muComics'])
    @role_required(["Comic Admin"])
    def get(self, request):
        queryset = ComicComment.objects.select_related(
            'user', 'comic', 'deleted_by'
        ).prefetch_related('replies').order_by('-created_at')

        # Filter by comic_id
        comic_id = request.query_params.get('comic_id')
        if comic_id:
            queryset = queryset.filter(comic_id=comic_id)

        # Filter by chapter_id
        chapter_id = request.query_params.get('chapter_id')
        if chapter_id:
            queryset = queryset.filter(chapter_id=chapter_id)

        # Filter by user_id
        user_id_filter = request.query_params.get('user_id')
        if user_id_filter:
            queryset = queryset.filter(user_id=user_id_filter)

        # Deleted filters
        include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
        deleted_only = request.query_params.get('deleted_only', 'false').lower() == 'true'

        if deleted_only:
            queryset = queryset.filter(deleted_at__isnull=False)
        elif not include_deleted:
            queryset = queryset.filter(deleted_at__isnull=True)

        paginated = CommonUtils.get_paginated_queryset(
            queryset,
            request,
            search_fields=['message'],
            sort_fields={'created_at': 'created_at'},
        )

        # Bulk fetch chapter titles for the paginated page
        chapter_ids = [c.chapter_id for c in paginated['queryset'] if c.chapter_id]
        chapter_titles = {}
        if chapter_ids:
            unique_chapter_ids = list(set(chapter_ids))
            from django.db import connection
            with connection.cursor() as cursor:
                format_strings = ','.join(['%s'] * len(unique_chapter_ids))
                cursor.execute(f"SELECT id, title FROM chapter WHERE id IN ({format_strings})", unique_chapter_ids)
                for row in cursor.fetchall():
                    chapter_titles[row[0]] = row[1]

        serializer = AdminCommentListSerializer(
            paginated['queryset'], many=True,
            context={'chapter_titles': chapter_titles}
        )

        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )


class AdminCommentDeleteAPI(APIView):
    """
    DELETE /admin/comments/<comment_id>/ — soft-delete any comment (moderator)
    """
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['muComics'])
    @role_required(["Comic Admin"])
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

        now = timezone.now()
        with transaction.atomic():
            comment.deleted_at = now
            comment.deleted_by_id = user_id
            comment.updated_at = now
            comment.updated_by_id = user_id
            comment.save()

            _decrement_comment_count(comment.comic_id)

        return CustomResponse(
            general_message="Comment removed by moderator"
        ).get_success_response()
