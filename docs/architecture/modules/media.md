# `media`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

Comics (chapters, pages, likes, bookmarks, comments, genres), media content and posters.

## Kind

Supporting.

## Tables it owns

`comic` and the `comic_*` tables, `chapter` (the comics chapter table), `chapter_page`, `genre`, `media_content`, `ig_media_content_link`.

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `chapter` | `api/muComics/chapter/chapter_views.py` :: `patch`<br>`api/muComics/chapter/chapter_views.py` :: `post`<br>`api/muComics/chapter/serializers.py` :: `create`<br>`api/muComics/chapter/serializers.py` :: `update` | — |
| `chapter_page` | `api/muComics/chapter/chapter_views.py` :: `delete`<br>`api/muComics/chapter/chapter_views.py` :: `patch`<br>`api/muComics/chapter/chapter_views.py` :: `post` | — |
| `comic` | `api/muComics/comic/comic_views.py` :: `patch`<br>`api/muComics/comic/comic_views.py` :: `post`<br>`api/muComics/comic/serializers.py` :: `create`<br>`api/muComics/comic/serializers.py` :: `update`<br>`api/muComics/comment/comment_views.py` :: `_decrement_comment_count`<br>`api/muComics/comment/comment_views.py` :: `_increment_comment_count`<br>`api/muComics/reader/interaction_views.py` :: `delete`<br>`api/muComics/reader/interaction_views.py` :: `post` | — |
| `comic_bookmark_link` | `api/muComics/reader/interaction_views.py` :: `delete`<br>`api/muComics/reader/interaction_views.py` :: `post`<br>`api/muComics/reader/serializers.py` :: `create` | — |
| `comic_comment` | `api/muComics/comment/admin_views.py` :: `delete`<br>`api/muComics/comment/comment_views.py` :: `delete`<br>`api/muComics/comment/comment_views.py` :: `patch`<br>`api/muComics/comment/comment_views.py` :: `post` | — |
| `comic_contributor_link` | `api/muComics/comic/serializers.py` :: `create` | — |
| `comic_genre_link` | `api/muComics/comic/comic_views.py` :: `delete`<br>`api/muComics/comic/serializers.py` :: `create` | — |
| `comic_like_link` | `api/muComics/reader/interaction_views.py` :: `delete`<br>`api/muComics/reader/interaction_views.py` :: `post`<br>`api/muComics/reader/serializers.py` :: `create` | — |
| `comic_reading_progress` | `api/muComics/reader/progress_views.py` :: `put`<br>`api/muComics/reader/serializers.py` :: `create` | — |
| `genre` | `api/muComics/comic/admin_views.py` :: `patch`<br>`api/muComics/comic/admin_views.py` :: `post`<br>`api/muComics/comic/serializers.py` :: `create`<br>`api/muComics/comic/serializers.py` :: `update` | — |
| `ig_media_content_link` | `api/dashboard/media_content/views.py` :: `_sync_ig_links`<br>`api/dashboard/media_content/views.py` :: `post` | — |
| `media_content` | `api/dashboard/media_content/views.py` :: `post`<br>`mu_celery/media_content_tasks.py` :: `fetch_and_attach_poster` | — |

## Public API (public.py)

`comic(slug)`.

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| `media.media_published` | none |

## Allowed dependencies

`people.public`, `identity_access.public`.

## What moves from legacy code

`api/muComics/`, `api/media/`, `api/dashboard/media_content/`, `mu_celery/media_content_tasks.py`.

## Cut-over steps

1. [Epic: Later: modules on demand and deferred items](../github-issues/epics/later-on-demand.md)

## Tests this module needs

- Files are stored by object key in R2, never on a node disk ([ADR-011](../adr/ADR-011-object-storage-stateless-nodes.md)).

## Open questions

None yet.
