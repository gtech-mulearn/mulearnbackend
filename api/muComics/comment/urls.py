from django.urls import path

from . import comment_views, admin_views

urlpatterns = [
    # Comic Comments
    path(
        'comic/<str:comic_id>/list/',
        comment_views.ComicCommentListAPI.as_view(),
        name='comic-comment-list',
    ),
    path(
        'comic/<str:comic_id>/create/',
        comment_views.ComicCommentCreateAPI.as_view(),
        name='comic-comment-create',
    ),

    # Chapter Comments
    path(
        'chapter/<str:chapter_id>/list/',
        comment_views.ChapterCommentListAPI.as_view(),
        name='chapter-comment-list',
    ),
    path(
        'chapter/<str:chapter_id>/create/',
        comment_views.ChapterCommentCreateAPI.as_view(),
        name='chapter-comment-create',
    ),

    # Admin — List All Comments
    path(
        'admin/',
        admin_views.AdminCommentListAPI.as_view(),
        name='admin-comment-list',
    ),

    # Admin — Delete Comment (Soft-Delete)
    path(
        'admin/<str:comment_id>/',
        admin_views.AdminCommentDeleteAPI.as_view(),
        name='admin-comment-delete',
    ),

    # Edit / Delete (User Soft-Delete)
    path(
        '<str:comment_id>/',
        comment_views.CommentDetailAPI.as_view(),
        name='comment-detail',
    ),
]
