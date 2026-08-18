from django.urls import path

from . import comic_views, admin_views

urlpatterns = [
    # ── Genre management (Admin) ──────────────────────────────────────────────
    # IMPORTANT: Must come BEFORE <str:comic_id>/ patterns to avoid shadowing.
    path('genres/',
         admin_views.GenreListCreateView.as_view(),
         name='genre-list-create'),

    path('genres/<str:genre_id>/',
         admin_views.GenreDetailView.as_view(),
         name='genre-detail'),

    path('genres/<str:genre_id>/reinstate/',
         admin_views.GenreReinstateView.as_view(),
         name='genre-reinstate'),

    # ── Comic CRUD ────────────────────────────────────────────────────────────
    # List + Create
    path('', comic_views.ComicListCreateView.as_view(), name='comic-list-create'),

    # Detail + Update + Delete
    path('<str:comic_id>/', comic_views.ComicDetailView.as_view(), name='comic-detail'),

    # Status workflow
    path('<str:comic_id>/publish/', comic_views.ComicPublishView.as_view(),  name='comic-publish'),
    path('<str:comic_id>/archive/', comic_views.ComicArchiveView.as_view(),  name='comic-archive'),
    path('<str:comic_id>/unarchive/', comic_views.ComicUnarchiveView.as_view(), name='comic-unarchive'),

    # Contributors
    path('<str:comic_id>/contributors/',
         comic_views.ComicContributorListView.as_view(),
         name='comic-contributor-list'),
    path('<str:comic_id>/contributors/<str:contributor_id>/',
         comic_views.ComicContributorDetailView.as_view(),
         name='comic-contributor-detail'),

    # Comic Genre Links
    path('<str:comic_id>/genres/',
         comic_views.ComicGenreListView.as_view(),
         name='comic-genre-assign'),
    path('<str:comic_id>/genres/<str:link_id>/',
         comic_views.ComicGenreDetailView.as_view(),
         name='comic-genre-remove'),
]

