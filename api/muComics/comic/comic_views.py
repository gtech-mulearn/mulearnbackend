"""
Comic CRUD views.

Endpoints:
  GET    /muComics/comics/                      → list (paginated, search, filter, sort)
  POST   /muComics/comics/                      → create (admin only)
  GET    /muComics/comics/<comic_id>/            → detail
  PATCH  /muComics/comics/<comic_id>/            → partial update (creator or editor)
  DELETE /muComics/comics/<comic_id>/            → soft delete (creator only)
  POST   /muComics/comics/<comic_id>/publish/    → draft → published (creator only)
  POST   /muComics/comics/<comic_id>/archive/    → published/draft → archived (creator only)
  POST   /muComics/comics/<comic_id>/unarchive/  → archived → draft (creator only)
"""

from django.utils import timezone
from django.db.models import Q
from django.db import IntegrityError

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s
from rest_framework.views import APIView

from db.comic import Comic, ComicContributorLink, ComicGenreLink, Genre
from utils.permission import CustomizePermission, OptionalAuthentication, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils
from utils.types import RoleType

from .serializers import (
    ComicListItemSerializer,
    ComicDetailSerializer,
    ComicWriteSerializer,
    ContributorWriteSerializer,
    ContributorRoleUpdateSerializer,
    ContributorListSerializer,
    ComicGenreAssignSerializer,
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_active_comics():
    """Base queryset: exclude soft-deleted rows."""
    return Comic.objects.filter(deleted_at__isnull=True)


def _is_creator_or_admin(user_id, comic, request):
    """
    True if the user is the comic's original creator
    OR holds the platform Admin role in their JWT.
    """
    if not user_id:
        return False
    if comic.created_by_id == user_id:
        return True
    return RoleType.ADMIN.value in JWTUtils.fetch_role(request)


def can_edit_comic(user_id, comic):
    """
    True if the user is the comic's creator OR has been explicitly assigned
    as an 'editor' contributor on that comic by the creator.
    """
    if not user_id:
        return False
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
    GET  /muComics/comics/  → paginated list with search, status filter, sort (Public for published comics)
    POST /muComics/comics/  → create a new comic (admin only)
    """
    authentication_classes = [OptionalAuthentication]

    @extend_schema(
        tags=['muComics'],
        description="List all active (non-deleted) comics. Supports search by title, status filter, and sort by created_at or title.",
        responses={200: ComicListItemSerializer(many=True)},
    )
    def get(self, request):
        is_authenticated = JWTUtils.is_logged_in(request)
        user_id = JWTUtils.fetch_user_id(request) if is_authenticated else None
        queryset = _get_active_comics()

        # Unauthenticated users can only see published comics
        if not is_authenticated:
            queryset = queryset.filter(status=Comic.Status.PUBLISHED)
        else:
            # Optional status filter: ?status=draft|published|archived
            if status_filter := request.query_params.get('status'):
                if status_filter not in Comic.Status.values:
                    return CustomResponse(
                        general_message=f'Invalid status. Allowed: {", ".join(Comic.Status.values)}.'
                    ).get_failure_response()
                queryset = queryset.filter(status=status_filter)

        # Optional multi-genre filter: ?genre=action,horror
        # Accepts one or more genre slugs (comma-separated).
        # Returns comics that have at least one of the given active genres.
        if genre_param := request.query_params.get('genre'):
            genre_slugs = [s.strip() for s in genre_param.split(',') if s.strip()]
          
            if genre_slugs:
                queryset = queryset.filter(
                    genre_links__genre__slug__in=genre_slugs,
                    genre_links__genre__is_active=True,
                ).distinct()

        paginated = CommonUtils.get_paginated_queryset(
            queryset.select_related('created_by').prefetch_related('genre_links__genre', 'contributor_links__user'),
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
        description="Create a new comic. Only admins may create. The creator is specified via creator_muid. Returns the full comic detail on success.",
        request=ComicWriteSerializer,
        responses={200: ComicDetailSerializer},
    )
    def post(self, request):
        if not JWTUtils.is_logged_in(request):
            return CustomResponse(
                general_message='Authentication credentials were not provided.'
            ).get_unauthorized_response()

        user_id = JWTUtils.fetch_user_id(request)

        # Only admins can create comics
        if RoleType.ADMIN.value not in JWTUtils.fetch_role(request):
            return CustomResponse(
                general_message='Only admins can create comics.'
            ).get_unauthorized_response()

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
    GET    /muComics/comics/<comic_id>/   → full detail (public for published comics)
    PATCH  /muComics/comics/<comic_id>/   → partial update (creator or assigned editor)
    DELETE /muComics/comics/<comic_id>/   → soft delete (creator only)
    """
    authentication_classes = [OptionalAuthentication]

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
        is_authenticated = JWTUtils.is_logged_in(request)
        user_id = JWTUtils.fetch_user_id(request) if is_authenticated else None
        comic, error = self._get_comic_or_error(comic_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response()

        # Unauthenticated users can only view published comics
        if not is_authenticated and comic.status != Comic.Status.PUBLISHED:
            return CustomResponse(general_message='Comic not found.').get_failure_response()

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
        if not JWTUtils.is_logged_in(request):
            return CustomResponse(
                general_message='Authentication credentials were not provided.'
            ).get_unauthorized_response()

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
        if not JWTUtils.is_logged_in(request):
            return CustomResponse(
                general_message='Authentication credentials were not provided.'
            ).get_unauthorized_response()

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


# ─────────────────────────────────────────────────────────────────────────────
# UNARCHIVE
# ─────────────────────────────────────────────────────────────────────────────

class ComicUnarchiveView(APIView):
    """
    POST /muComics/comics/<comic_id>/unarchive/
    Transitions an archived comic back to draft (creator only).

    Workflow:
        archived  → draft  ✅
        draft     → ❌  (not archived)
        published → ❌  (not archived)
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['muComics'],
        description="Unarchive an archived comic (archived → draft). Only the creator may unarchive. Non-archived comics are rejected.",
        responses={200: inline_serializer(
            name='ComicUnarchiveResponse',
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

        # Only creator can unarchive
        if comic.created_by_id != user_id:
            return CustomResponse(
                general_message='Only the comic creator can unarchive this comic.'
            ).get_unauthorized_response()

        if comic.status != Comic.Status.ARCHIVED:
            return CustomResponse(
                general_message='Only archived comics can be unarchived.'
            ).get_failure_response()

        now = timezone.now()
        comic.status        = Comic.Status.DRAFT
        comic.updated_by_id = user_id
        comic.updated_at    = now
        comic.save(update_fields=['status', 'updated_by', 'updated_at'])

        return CustomResponse(
            general_message=f'Comic "{comic.title}" unarchived successfully.',
            response={'id': comic.id, 'status': Comic.Status.DRAFT},
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# CONTRIBUTORS
# ─────────────────────────────────────────────────────────────────────────────

class ComicContributorListView(APIView):
    """
    GET  /muComics/comics/<comic_id>/contributors/
         → list all contributors for the comic (public)

    POST /muComics/comics/<comic_id>/contributors/
         → add a contributor (comic creator or Admin only)
         Request body: { "muid": "...", "role": "ARTIST" }
    """
    authentication_classes = [OptionalAuthentication]

    @extend_schema(
        tags=['muComics'],
        description="List all contributors for a comic.",
        responses={200: ContributorListSerializer(many=True)},
    )
    # def get(self, request, comic_id):
    #     comic = _get_active_comics().filter(id=comic_id).first()
    #     if not comic:
    #         return CustomResponse(general_message='Comic not found.').get_failure_response()

    #     role_filter = request.query_params.get('role')
    #     links = ComicContributorLink.objects.filter(comic=comic)
        
    #     if role_filter:
    #         links = links.filter(contributor_type=role_filter)
            
    #     links = links.select_related('user', 'comic')
        
    #     if not links:
    #         if role_filter:
    #             return CustomResponse(general_message=f'No {role_filter} contributor found for this comic.', response=[]).get_success_response()
    #         return CustomResponse(general_message='There are no contributors for this comic.', response=[]).get_success_response()
            
    #     serializer = ContributorListSerializer(links, many=True)
    #     return CustomResponse(response=serializer.data).get_success_response()
    def get(self, request, comic_id):
        is_authenticated = JWTUtils.is_logged_in(request)
        comic = _get_active_comics().filter(id=comic_id).first()
        if not comic:
            return CustomResponse(general_message='Comic not found.').get_failure_response()

        # Unauthenticated users can only view contributors for published comics
        if not is_authenticated and comic.status != Comic.Status.PUBLISHED:
            return CustomResponse(general_message='Comic not found.').get_failure_response()

        links = ComicContributorLink.objects.filter(comic=comic).select_related('user', 'comic')

        role_filter = request.query_params.get('role')
        if role_filter:
            links = links.filter(contributor_type=role_filter)

        paginated = CommonUtils.get_paginated_queryset(
            links,
            request,
            search_fields=['user__full_name', 'contributor_type'],
            sort_fields={'role': 'contributor_type'},
        )

        serializer = ContributorListSerializer(paginated['queryset'], many=True)
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )

    @extend_schema(
        tags=['muComics'],
        description="Add a contributor to a comic by muid and role. Only the comic creator or an Admin may call this. The CREATOR role cannot be assigned via this endpoint.",
        request=ContributorWriteSerializer,
        responses={200: inline_serializer(
            name='ContributorAddResponse',
            fields={'message': s.CharField()},
        )},
    )
    def post(self, request, comic_id):
        if not JWTUtils.is_logged_in(request):
            return CustomResponse(
                general_message='Authentication credentials were not provided.'
            ).get_unauthorized_response()

        user_id = JWTUtils.fetch_user_id(request)
        comic   = _get_active_comics().filter(id=comic_id).first()
        if not comic:
            return CustomResponse(general_message='Comic not found.').get_failure_response()

        if not _is_creator_or_admin(user_id, comic, request):
            return CustomResponse(
                general_message='Only the comic creator or an admin can add contributors.'
            ).get_unauthorized_response()

        serializer = ContributorWriteSerializer(
            data=request.data,
            context={'comic': comic, 'user_id': user_id},
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()

        try:
            serializer.save()
        except IntegrityError:
            return CustomResponse(
                general_message='Contributor with this role already exists.'
            ).get_failure_response()

        # muid comes from validated_data['muid'] which is a User object after validate_muid
        muid = serializer.validated_data['muid'].muid
        role = serializer.validated_data['role']
        return CustomResponse(
            general_message=f'{role} {muid} added successfully.'
        ).get_success_response()


class ComicContributorDetailView(APIView):
    """
    PATCH  /muComics/comics/<comic_id>/contributors/<contributor_id>/
           → update a contributor's role (comic creator or Admin only)

    DELETE /muComics/comics/<comic_id>/contributors/<contributor_id>/
           → remove a contributor (comic creator or Admin only)
    """
    authentication_classes = [CustomizePermission]

    def _get_link_or_error(self, comic, contributor_id):
        """Fetch a ComicContributorLink by PK scoped to the given comic."""
        link = (
            ComicContributorLink.objects
            .filter(id=contributor_id, comic=comic)
            .select_related('user')
            .first()
        )
        if not link:
            return None, 'Contributor not found.'
        return link, None

    @extend_schema(
        tags=['muComics'],
        description="Update a contributor's role. Only the comic creator or an Admin may call this. The CREATOR role cannot be assigned.",
        request=ContributorRoleUpdateSerializer,
        responses={200: inline_serializer(
            name='ContributorUpdateResponse',
            fields={'message': s.CharField()},
        )},
    )
    def patch(self, request, comic_id, contributor_id):
        user_id = JWTUtils.fetch_user_id(request)
        comic   = _get_active_comics().filter(id=comic_id).first()
        if not comic:
            return CustomResponse(general_message='Comic not found.').get_failure_response()

        if not _is_creator_or_admin(user_id, comic, request):
            return CustomResponse(
                general_message='Only the comic creator or an admin can update contributors.'
            ).get_unauthorized_response()

        link, error = self._get_link_or_error(comic, contributor_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response()

        serializer = ContributorRoleUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()

        link.contributor_type = serializer.validated_data['role']
        try:
            link.save(update_fields=['contributor_type'])
        except IntegrityError:
            return CustomResponse(
                general_message='Contributor with this role already exists.'
            ).get_failure_response()

        return CustomResponse(
            general_message=f'{link.contributor_type} {link.user.muid} updated.'
        ).get_success_response()

    @extend_schema(
        tags=['muComics'],
        description="Remove a contributor from a comic. Only the comic creator or an Admin may call this.",
        responses={200: inline_serializer(
            name='ContributorRemoveResponse',
            fields={'message': s.CharField()},
        )},
    )
    def delete(self, request, comic_id, contributor_id):
        user_id = JWTUtils.fetch_user_id(request)
        comic   = _get_active_comics().filter(id=comic_id).first()
        if not comic:
            return CustomResponse(general_message='Comic not found.').get_failure_response()

        if not _is_creator_or_admin(user_id, comic, request):
            return CustomResponse(
                general_message='Only the comic creator or an admin can remove contributors.'
            ).get_unauthorized_response()

        link, error = self._get_link_or_error(comic, contributor_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response()

        muid = link.user.muid
        role=link.contributor_type
        link.delete()

        return CustomResponse(
            general_message=f'{role} {muid} removed.'
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# COMIC GENRE LINKS (assign / remove)
# ─────────────────────────────────────────────────────────────────────────────

class ComicGenreListView(APIView):
    """
    POST /muComics/comics/<comic_id>/genres/
         Assign a genre to a comic.
         Required role: Creator, Editor or Admin
         Request body: { "genre_id": "<uuid>" }
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['muComics'],
        description="Assign a genre to a comic. Only the creator, an assigned editor, or an admin might perform this action.",
        request=ComicGenreAssignSerializer,
        responses={200: inline_serializer(
            name='ComicGenreAssignResponse',
            fields={
                'link_id': s.CharField(),
                'genre': inline_serializer(
                    name='GenreMinimalObj',
                    fields={
                        'id': s.CharField(),
                        'name': s.CharField(),
                        'slug': s.CharField(),
                    }
                )
            }
        )},
    )
    def post(self, request, comic_id):
        user_id = JWTUtils.fetch_user_id(request)
        comic = _get_active_comics().filter(id=comic_id).first()
        if not comic:
            return CustomResponse(general_message='Comic not found.').get_failure_response()

        # Permission role check: Creator, Editor or Admin
        if not (can_edit_comic(user_id, comic) or RoleType.ADMIN.value in JWTUtils.fetch_role(request)):
            return CustomResponse(
                general_message='Only the comic creator, assigned editor, or an Admin can manage genres for this comic.'
            ).get_unauthorized_response()

        serializer = ComicGenreAssignSerializer(
            data=request.data,
            context={'comic': comic, 'user_id': user_id},
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()

        try:
            link = serializer.save()
        except IntegrityError:
            return CustomResponse(
                general_message='This genre is already assigned to this comic.'
            ).get_failure_response()

        return CustomResponse(
            general_message=f'Genre "{link.genre.name}" assigned to comic "{comic.title}" successfully.',
            response={
                'link_id': link.id,
                'genre': {
                    'id': link.genre.id,
                    'name': link.genre.name,
                    'slug': link.genre.slug,
                }
            },
        ).get_success_response()


class ComicGenreDetailView(APIView):
    """
    DELETE /muComics/comics/<comic_id>/genres/<link_id>/
           Remove a genre link from a comic.
           Required role: Creator, Editor or Admin
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['muComics'],
        description="Remove a genre from a comic. Only the creator, an assigned editor, or an admin might perform this action.",
        responses={200: inline_serializer(
            name='ComicGenreRemoveResponse',
            fields={'link_id': s.CharField()}
        )},
    )
    def delete(self, request, comic_id, link_id):
        user_id = JWTUtils.fetch_user_id(request)
        comic = _get_active_comics().filter(id=comic_id).first()
        if not comic:
            return CustomResponse(general_message=f'Comic {comic_id} not found.').get_failure_response()

        # Permission role check: Creator, Editor or Admin
        if not (can_edit_comic(user_id, comic) or RoleType.ADMIN.value in JWTUtils.fetch_role(request)):
            return CustomResponse(
                general_message='Only the comic creator, assigned editor, or an Admin can manage genres for this comic.'
            ).get_unauthorized_response()

        link = ComicGenreLink.objects.filter(id=link_id, comic=comic).select_related('genre').first()
        if not link:
            return CustomResponse(
                general_message='Genre link not found for this comic.'
            ).get_failure_response()

        genre_name = link.genre.name
        link.delete()

        return CustomResponse(
            general_message=f'Genre "{genre_name}" removed from comic "{comic.title}" successfully.',
            response={'link_id': link_id},
        ).get_success_response()

