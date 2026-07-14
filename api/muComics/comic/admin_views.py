"""
Genre admin views — embedded in the comic module.

Endpoints (all authenticated; writes require Admins role):
  GET    /muComics/comics/genres/                      → list (active only for non-admin; admin can filter ?is_active=)
  POST   /muComics/comics/genres/                      → create  [Admin]
  GET    /muComics/comics/genres/<genre_id>/           → detail  (active for non-admin; any for admin)
  PATCH  /muComics/comics/genres/<genre_id>/           → update name  [Admin]
  DELETE /muComics/comics/genres/<genre_id>/           → soft deactivate (is_active=False)  [Admin]
  POST   /muComics/comics/genres/<genre_id>/reinstate/ → reactivate (is_active=True)  [Admin]
"""

from django.utils import timezone

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s
from rest_framework.views import APIView

from db.comic import Genre
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils

from .serializers import GenreReadSerializer, GenreWriteSerializer


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _is_admin(request):
    """Return True if the JWT carries the Admins role."""
    return RoleType.ADMIN.value in JWTUtils.fetch_role(request)


# ─────────────────────────────────────────────────────────────────────────────
# GENRE LIST + CREATE
# ─────────────────────────────────────────────────────────────────────────────

class GenreListCreateView(APIView):
    """
    GET  /muComics/comics/genres/
         Non-admins → only is_active=True genres.
         Admins     → all genres; optionally filter with ?is_active=true|false.

    POST /muComics/comics/genres/  [Admin only]
         Create a new genre (is_active defaults to True).
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['muComics - Genre'],
        description=(
            "List genres. Non-admins see only active genres. "
            "Admins can filter with ?is_active=true|false. "
            "Supports ?search= (by name) and ?sort=name|created_at."
        ),
        responses={200: GenreReadSerializer(many=True)},
    )
    def get(self, request):
        admin = _is_admin(request)

        if admin:
            queryset = Genre.objects.all()
            is_active_param = request.query_params.get('is_active')
            if is_active_param is not None:
                if is_active_param.lower() == 'true':
                    queryset = queryset.filter(is_active=True)
                elif is_active_param.lower() == 'false':
                    queryset = queryset.filter(is_active=False)
                else:
                    return CustomResponse(
                        general_message='Invalid value for is_active. Use true or false.'
                    ).get_failure_response()
        else:
            # Regular users only ever see active genres
            queryset = Genre.objects.filter(is_active=True)

        paginated = CommonUtils.get_paginated_queryset(
            queryset,
            request,
            search_fields=['name'],
            sort_fields={
                'name':       'name',
                'created_at': 'created_at',
            },
        )

        serializer = GenreReadSerializer(paginated['queryset'], many=True)
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )

    @extend_schema(
        tags=['muComics - Genre'],
        description="Create a new genre. is_active defaults to true. Admin only.",
        request=GenreWriteSerializer,
        responses={200: GenreReadSerializer},
    )
    @RoleRequired([RoleType.ADMIN])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        serializer = GenreWriteSerializer(
            data=request.data,
            context={'user_id': user_id},
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response("")

        genre = serializer.save()

        return CustomResponse(
            general_message=f'Genre "{genre.name}" created successfully.',
            response=GenreReadSerializer(genre).data,
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# GENRE DETAIL — GET / PATCH / DELETE (soft deactivate)
# ─────────────────────────────────────────────────────────────────────────────

class GenreDetailView(APIView):
    """
    GET    → active genres only for non-admins; any genre for admins.
    PATCH  → update name (Admin only).
    DELETE → soft deactivate: is_active = False (Admin only).
    """
    authentication_classes = [CustomizePermission]

    def _get_genre(self, genre_id, admin):
        """
        Fetch genre by id.
        - Admin: any genre (active or inactive).
        - Non-admin: only active genres.
        Returns (genre, error_string).
        """
        qs = Genre.objects.all() if admin else Genre.objects.filter(is_active=True)
        genre = qs.filter(id=genre_id).first()
        if not genre:
            return None, 'Genre not found.'
        return genre, None

    @extend_schema(
        tags=['muComics - Genre'],
        description=(
            "Retrieve a genre. Non-admins only see active genres (inactive → 404). "
            "Admins can retrieve any genre regardless of is_active status."
        ),
        responses={200: GenreReadSerializer},
    )
    def get(self, request, genre_id):
        admin = _is_admin(request)
        genre, error = self._get_genre(genre_id, admin)
        if error:
            return CustomResponse(general_message=error).get_failure_response()

        return CustomResponse(
            general_message=f'Genre "{genre.name}" retrieved successfully.',
            response=GenreReadSerializer(genre).data,
        ).get_success_response()

    @extend_schema(
        tags=['muComics - Genre'],
        description="Update a genre's name (slug is regenerated automatically). Admin only.",
        request=GenreWriteSerializer,
        responses={200: GenreReadSerializer},
    )
    @RoleRequired([RoleType.ADMIN])
    def patch(self, request, genre_id):
        user_id = JWTUtils.fetch_user_id(request)
        # Admin context — can edit active or inactive genre
        genre, error = self._get_genre(genre_id, admin=True)
        if error:
            return CustomResponse(general_message=error).get_failure_response()

        serializer = GenreWriteSerializer(
            genre,
            data=request.data,
            partial=True,
            context={'user_id': user_id},
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()

        genre = serializer.save()

        return CustomResponse(
            general_message=f'Genre "{genre.name}" updated successfully.',
            response=GenreReadSerializer(genre).data,
        ).get_success_response()

    @extend_schema(
        tags=['muComics - Genre'],
        description=(
            "Soft-deactivate a genre (sets is_active = False). "
            "The genre row and all comic_genre_link rows are preserved. "
            "Admin only."
        ),
        responses={200: inline_serializer(
            name='GenreDeactivateResponse',
            fields={
                'id':        s.CharField(),
                'is_active': s.BooleanField(),
            },
        )},
    )
    @RoleRequired([RoleType.ADMIN])
    def delete(self, request, genre_id):
        user_id = JWTUtils.fetch_user_id(request)
        genre, error = self._get_genre(genre_id, admin=True)
        if error:
            return CustomResponse(general_message=error).get_failure_response()

        if not genre.is_active:
            return CustomResponse(
                general_message=f'Genre "{genre.name}" is already inactive.'
            ).get_failure_response()

        now                 = timezone.now()
        genre.is_active     = False
        genre.updated_by_id = user_id
        genre.updated_at    = now
        genre.save(update_fields=['is_active', 'updated_by', 'updated_at'])

        return CustomResponse(
            general_message=f'Genre "{genre.name}" deactivated successfully.',
            response={'id': genre.id, 'is_active': False},
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# GENRE REINSTATE
# ─────────────────────────────────────────────────────────────────────────────

class GenreReinstateView(APIView):
    """
    POST /muComics/comics/genres/<genre_id>/reinstate/
    Reactivates a deactivated genre (is_active = True). Admin only.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['muComics - Genre'],
        description="Reinstate (reactivate) a deactivated genre. Sets is_active = True. Admin only.",
        responses={200: inline_serializer(
            name='GenreReinstateResponse',
            fields={
                'id':        s.CharField(),
                'is_active': s.BooleanField(),
            },
        )},
    )
    @RoleRequired([RoleType.ADMIN])
    def post(self, request, genre_id):
        user_id = JWTUtils.fetch_user_id(request)
        # Admin needed — fetch any genre (active or inactive)
        genre = Genre.objects.filter(id=genre_id).first()
        if not genre:
            return CustomResponse(general_message='Genre not found.').get_failure_response()

        if genre.is_active:
            return CustomResponse(
                general_message=f'Genre "{genre.name}" is already active.'
            ).get_failure_response()

        now                 = timezone.now()
        genre.is_active     = True
        genre.updated_by_id = user_id
        genre.updated_at    = now
        genre.save(update_fields=['is_active', 'updated_by', 'updated_at'])

        return CustomResponse(
            general_message=f'Genre "{genre.name}" reinstated successfully.',
            response={'id': genre.id, 'is_active': True},
        ).get_success_response()
