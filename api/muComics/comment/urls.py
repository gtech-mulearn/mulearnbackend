from django.urls import path

from . import comment_views, admin_views

urlpatterns = [
    # Endpoint 1 & 3: List / Create Comic Comments
    path(
        'comic/<str:comic_id>/',
        comment_views.ComicCommentListCreateAPI.as_view(),
        name='comic-comment-list-create',
    ),

    # Endpoint 2 & 4: List / Create Chapter Comments
    path(
        'chapter/<str:chapter_id>/',
        comment_views.ChapterCommentListCreateAPI.as_view(),
        name='chapter-comment-list-create',
    ),

    # Endpoint 7: Admin — List All Comments
    path(
        'admin/',
        admin_views.AdminCommentListAPI.as_view(),
        name='admin-comment-list',
    ),

    # Endpoint 8: Admin — Delete Comment (Soft-Delete)
    path(
        'admin/<str:comment_id>/',
        admin_views.AdminCommentDeleteAPI.as_view(),
        name='admin-comment-delete',
    ),

    # Endpoint 5 & 6: Edit / Delete (User Soft-Delete)
    path(
        '<str:comment_id>/',
        comment_views.CommentDetailAPI.as_view(),
        name='comment-detail',
    ),
]
