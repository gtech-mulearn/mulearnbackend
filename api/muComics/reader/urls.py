from django.urls import path
from . import interaction_views, progress_views, dashboard_views

urlpatterns = [
    # Dashboard
    path('me/', dashboard_views.ReaderDashboardAPI.as_view()),
    path('me/bookmarks/', dashboard_views.MyBookmarksAPI.as_view()),
    path('me/progress/', dashboard_views.MyReadingProgressAPI.as_view()),
    
    # Interactions
    path('comics/<str:comic_id>/likes/', interaction_views.LikeComicAPI.as_view()),
    path('comics/<str:comic_id>/bookmarks/', interaction_views.BookmarkComicAPI.as_view()),
    path('comics/<str:comic_id>/interaction-status/', interaction_views.InteractionStatusAPI.as_view()),
    
    # Progress
    path('comics/<str:comic_id>/progress/', progress_views.ReadingProgressAPI.as_view()),
]
