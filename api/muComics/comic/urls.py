from django.urls import path

from . import comic_views

urlpatterns = [
    # List + Create
    path('',                         comic_views.ComicListCreateView.as_view(),  name='comic-list-create'),

    # Detail + Update + Delete
    path('<str:comic_id>/',          comic_views.ComicDetailView.as_view(),      name='comic-detail'),

    # Status workflow
    path('<str:comic_id>/publish/',  comic_views.ComicPublishView.as_view(),     name='comic-publish'),
    path('<str:comic_id>/archive/',  comic_views.ComicArchiveView.as_view(),     name='comic-archive'),

    # Contributors
    path('<str:comic_id>/contributors/',
         comic_views.ComicContributorListView.as_view(),
         name='comic-contributor-list'),
    path('<str:comic_id>/contributors/<str:contributor_id>/',
         comic_views.ComicContributorDetailView.as_view(),
         name='comic-contributor-detail'),
]
