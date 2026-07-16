from django.urls import path

from . import chapter_views

urlpatterns = [
    # Upload helper API (positioned first to avoid conflict with chapter_id string parameter)
    path('upload-url/',                                 chapter_views.ChapterUploadURLAPI.as_view(),     name='chapter-upload-url'),

    # Chapters List + Create
    path('',                                            chapter_views.ChapterListCreateView.as_view(),   name='chapter-list-create'),
    
    # Chapter Detail + Update + Delete
    path('<str:chapter_id>/',                           chapter_views.ChapterDetailView.as_view(),       name='chapter-detail'),
    
    # Chapter Status actions
    path('<str:chapter_id>/publish/',                   chapter_views.ChapterPublishView.as_view(),      name='chapter-publish'),
    path('<str:chapter_id>/archive/',                   chapter_views.ChapterArchiveView.as_view(),      name='chapter-archive'),
    
    # Pages List + Add
    path('<str:chapter_id>/pages/',                     chapter_views.ChapterPageListCreateAPI.as_view(), name='chapter-page-list-create'),
    
    # Reorder Pages
    path('<str:chapter_id>/pages/reorder/',             chapter_views.ChapterPageReorderAPI.as_view(),   name='chapter-page-reorder'),
    
    # Register Uploaded Images as Pages
    path('<str:chapter_id>/pages/register/',            chapter_views.ChapterRegisterImagesAPI.as_view(), name='chapter-page-register-images'),
    
    # Page Detail (Update / Delete)
    path('pages/<str:page_id>/',                        chapter_views.ChapterPageDetailAPI.as_view(),     name='chapter-page-detail'),
]
