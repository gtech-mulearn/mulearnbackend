"""
Media Content API views.

Exposes CRUD endpoints for three CMS-migrated content types backed by the
single ``MediaContent`` model:

  - Office Hours          → /media-content/office-hours/
  - Salt Mango Tree       → /media-content/salt-mango-tree/
  - Inspiration Station   → /media-content/inspiration-station/

Read (GET) endpoints are publicly accessible.
Write (POST / PATCH / DELETE) endpoints require the ADMIN role.
"""
import uuid

from django.utils import timezone
from rest_framework.views import APIView

from db.events import MediaContent
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils

from .serializers import (
    OfficeHoursReadSerializer,
    OfficeHoursWriteSerializer,
    SaltMangoTreeReadSerializer,
    SaltMangoTreeWriteSerializer,
    InspirationStationReadSerializer,
    InspirationStationWriteSerializer,
)

from drf_spectacular.utils import extend_schema


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

class PublicGetMixin:
    """
    Mixin to bypass JWT authentication for GET requests.
    """
    def get_authenticators(self):
        if getattr(self, 'request', None) and self.request.method == 'GET':
            return []
        return super().get_authenticators()

def _base_qs(content_type: str):
    """Live (non-deleted) queryset for a given content type."""
    return MediaContent.objects.filter(
        content_type=content_type,
        deleted_at__isnull=True,
    ).order_by('-date', '-created_at')


def _apply_common_filters(qs, request, *, has_zone: bool = False):
    """Apply shared query-param filters to a MediaContent queryset."""
    params = request.query_params
    from datetime import date

    if status := params.get('status'):
        status = status.lower()
        if status == 'upcoming':
            qs = qs.filter(date__gt=date.today())
        elif status == 'ongoing':
            qs = qs.filter(date=date.today())
        elif status == 'completed':
            qs = qs.filter(date__lt=date.today())

    if has_zone:
        if zone := params.get('zone'):
            qs = qs.filter(zone=zone)

    return qs


# ─────────────────────────────────────────────────────────────────────────────
# Office Hours
# ─────────────────────────────────────────────────────────────────────────────





class OfficeHoursListCreateAPI(PublicGetMixin, APIView):
    """
    GET  /media-content/office-hours/  — Public paginated list of sessions.
    POST /media-content/office-hours/  — Create a session (Admin only).
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Media Content - Office Hours'])
    def get(self, request):
        qs = _base_qs(MediaContent.ContentType.OFFICE_HOURS)
        qs = _apply_common_filters(qs, request, has_zone=False)

        paginated = CommonUtils.get_paginated_queryset(
            qs, request,
            search_fields=['title', 'performer', 'description'],
            sort_fields={
                'date': 'date',
                'created_at': 'created_at',
            },
        )

        serializer = OfficeHoursReadSerializer(paginated['queryset'], many=True)
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )


    @extend_schema(tags=['Media Content - Office Hours'])
    @RoleRequired([RoleType.ADMIN.value, RoleType.ASSOCIATE.value, RoleType.IG_LEAD.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = OfficeHoursWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                general_message='Invalid data.',
                message=serializer.errors,
            ).get_failure_response()

        data = serializer.validated_data
        record = MediaContent.objects.create(
            id=str(uuid.uuid4()),
            created_by_id=user_id,
            updated_by_id=user_id,
            **data,
        )

        return CustomResponse(
            general_message='Office Hours session created successfully.',
            response=OfficeHoursReadSerializer(record).data,
        ).get_success_response()


class OfficeHoursDetailAPI(PublicGetMixin, APIView):
    """
    GET    /media-content/office-hours/<record_id>/  — Public session detail.
    PATCH  /media-content/office-hours/<record_id>/  — Partial update (Admin only).
    DELETE /media-content/office-hours/<record_id>/  — Soft-delete (Admin only).
    """
    authentication_classes = [CustomizePermission]

    def _get_record(self, record_id):
        return MediaContent.objects.filter(
            id=record_id,
            content_type=MediaContent.ContentType.OFFICE_HOURS,
            deleted_at__isnull=True,
        ).first()

    @extend_schema(tags=['Media Content - Office Hours'])
    def get(self, request, record_id):
        record = self._get_record(record_id)
        if not record:
            return CustomResponse(
                general_message='Office Hours session not found.'
            ).get_failure_response()

        serializer = OfficeHoursReadSerializer(record)
        return CustomResponse(
            general_message='Office Hours session retrieved.',
            response=serializer.data,
        ).get_success_response()


    @extend_schema(tags=['Media Content - Office Hours'])
    @RoleRequired([RoleType.ADMIN.value, RoleType.ASSOCIATE.value, RoleType.IG_LEAD.value])
    def patch(self, request, record_id):
        record = self._get_record(record_id)
        if not record:
            return CustomResponse(
                general_message='Office Hours session not found.'
            ).get_failure_response()

        serializer = OfficeHoursWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return CustomResponse(
                general_message='Invalid data.',
                message=serializer.errors,
            ).get_failure_response()

        user_id = JWTUtils.fetch_user_id(request)
        data = serializer.validated_data
        data.pop('content_type', None)  # never allow overriding the discriminator

        for attr, value in data.items():
            setattr(record, attr, value)
        record.updated_by_id = user_id
        record.save()

        return CustomResponse(
            general_message='Office Hours session updated.',
            response=OfficeHoursReadSerializer(record).data,
        ).get_success_response()


    @extend_schema(tags=['Media Content - Office Hours'])
    @RoleRequired([RoleType.ADMIN.value, RoleType.ASSOCIATE.value, RoleType.IG_LEAD.value])
    def delete(self, request, record_id):
        record = self._get_record(record_id)
        if not record:
            return CustomResponse(
                general_message='Office Hours session not found.'
            ).get_failure_response()

        record.deleted_at = timezone.now()
        record.updated_by_id = JWTUtils.fetch_user_id(request)
        record.save(update_fields=['deleted_at', 'updated_by_id'])

        return CustomResponse(
            general_message='Office Hours session deleted.'
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# Salt Mango Tree
# ─────────────────────────────────────────────────────────────────────────────

class SaltMangoTreeListCreateAPI(PublicGetMixin, APIView):
    """
    GET  /media-content/salt-mango-tree/  — Public paginated list of episodes.
    POST /media-content/salt-mango-tree/  — Create an episode (Admin only).
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Media Content - Salt Mango Tree'])
    def get(self, request):
        qs = _base_qs(MediaContent.ContentType.SALT_MANGO_TREE)
        qs = _apply_common_filters(qs, request, has_zone=True)

        paginated = CommonUtils.get_paginated_queryset(
            qs, request,
            search_fields=['title', 'campus', 'description'],
            sort_fields={
                'date': 'date',
                'campus': 'campus',
                'created_at': 'created_at',
            },
        )

        serializer = SaltMangoTreeReadSerializer(paginated['queryset'], many=True)
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )

    @extend_schema(tags=['Media Content - Salt Mango Tree'])
    @RoleRequired([RoleType.ADMIN.value, RoleType.ASSOCIATE.value, RoleType.IG_LEAD.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = SaltMangoTreeWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                general_message='Invalid data.',
                message=serializer.errors,
            ).get_failure_response()

        data = serializer.validated_data
        record = MediaContent.objects.create(
            id=str(uuid.uuid4()),
            created_by_id=user_id,
            updated_by_id=user_id,
            **data,
        )

        return CustomResponse(
            general_message='Salt Mango Tree episode created successfully.',
            response=SaltMangoTreeReadSerializer(record).data,
        ).get_success_response()


class SaltMangoTreeDetailAPI(PublicGetMixin, APIView):
    """
    GET    /media-content/salt-mango-tree/<record_id>/
    PATCH  /media-content/salt-mango-tree/<record_id>/  (Admin)
    DELETE /media-content/salt-mango-tree/<record_id>/  (Admin)
    """
    authentication_classes = [CustomizePermission]

    def _get_record(self, record_id):
        return MediaContent.objects.filter(
            id=record_id,
            content_type=MediaContent.ContentType.SALT_MANGO_TREE,
            deleted_at__isnull=True,
        ).first()

    @extend_schema(tags=['Media Content - Salt Mango Tree'])
    def get(self, request, record_id):
        record = self._get_record(record_id)
        if not record:
            return CustomResponse(
                general_message='Salt Mango Tree episode not found.'
            ).get_failure_response()

        return CustomResponse(
            general_message='Salt Mango Tree episode retrieved.',
            response=SaltMangoTreeReadSerializer(record).data,
        ).get_success_response()

    @extend_schema(tags=['Media Content - Salt Mango Tree'])
    @RoleRequired([RoleType.ADMIN.value, RoleType.ASSOCIATE.value, RoleType.IG_LEAD.value])
    def patch(self, request, record_id):
        record = self._get_record(record_id)
        if not record:
            return CustomResponse(
                general_message='Salt Mango Tree episode not found.'
            ).get_failure_response()

        serializer = SaltMangoTreeWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return CustomResponse(
                general_message='Invalid data.',
                message=serializer.errors,
            ).get_failure_response()

        user_id = JWTUtils.fetch_user_id(request)
        data = serializer.validated_data
        data.pop('content_type', None)

        for attr, value in data.items():
            setattr(record, attr, value)
        record.updated_by_id = user_id
        record.save()

        return CustomResponse(
            general_message='Salt Mango Tree episode updated.',
            response=SaltMangoTreeReadSerializer(record).data,
        ).get_success_response()

    @extend_schema(tags=['Media Content - Salt Mango Tree'])
    @RoleRequired([RoleType.ADMIN.value, RoleType.ASSOCIATE.value, RoleType.IG_LEAD.value])
    def delete(self, request, record_id):
        record = self._get_record(record_id)
        if not record:
            return CustomResponse(
                general_message='Salt Mango Tree episode not found.'
            ).get_failure_response()

        record.deleted_at = timezone.now()
        record.updated_by_id = JWTUtils.fetch_user_id(request)
        record.save(update_fields=['deleted_at', 'updated_by_id'])

        return CustomResponse(
            general_message='Salt Mango Tree episode deleted.'
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# Inspiration Station Radio
# ─────────────────────────────────────────────────────────────────────────────

class InspirationStationListCreateAPI(PublicGetMixin, APIView):
    """
    GET  /media-content/inspiration-station/  — Public paginated list.
    POST /media-content/inspiration-station/  — Create an episode (Admin only).
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Media Content - Inspiration Station'])
    def get(self, request):
        qs = _base_qs(MediaContent.ContentType.INSPIRATION_STATION)
        qs = _apply_common_filters(qs, request, has_zone=True)

        paginated = CommonUtils.get_paginated_queryset(
            qs, request,
            search_fields=['title', 'campus', 'description'],
            sort_fields={
                'date': 'date',
                'campus': 'campus',
                'created_at': 'created_at',
            },
        )

        serializer = InspirationStationReadSerializer(paginated['queryset'], many=True)
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )

    @extend_schema(tags=['Media Content - Inspiration Station'])
    @RoleRequired([RoleType.ADMIN.value, RoleType.ASSOCIATE.value, RoleType.IG_LEAD.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = InspirationStationWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                general_message='Invalid data.',
                message=serializer.errors,
            ).get_failure_response()

        data = serializer.validated_data
        record = MediaContent.objects.create(
            id=str(uuid.uuid4()),
            created_by_id=user_id,
            updated_by_id=user_id,
            **data,
        )

        return CustomResponse(
            general_message='Inspiration Station episode created successfully.',
            response=InspirationStationReadSerializer(record).data,
        ).get_success_response()


class InspirationStationDetailAPI(PublicGetMixin, APIView):
    """
    GET    /media-content/inspiration-station/<record_id>/
    PATCH  /media-content/inspiration-station/<record_id>/  (Admin)
    DELETE /media-content/inspiration-station/<record_id>/  (Admin)
    """
    authentication_classes = [CustomizePermission]

    def _get_record(self, record_id):
        return MediaContent.objects.filter(
            id=record_id,
            content_type=MediaContent.ContentType.INSPIRATION_STATION,
            deleted_at__isnull=True,
        ).first()

    @extend_schema(tags=['Media Content - Inspiration Station'])
    def get(self, request, record_id):
        record = self._get_record(record_id)
        if not record:
            return CustomResponse(
                general_message='Inspiration Station episode not found.'
            ).get_failure_response()

        return CustomResponse(
            general_message='Inspiration Station episode retrieved.',
            response=InspirationStationReadSerializer(record).data,
        ).get_success_response()

    @extend_schema(tags=['Media Content - Inspiration Station'])
    @RoleRequired([RoleType.ADMIN.value, RoleType.ASSOCIATE.value, RoleType.IG_LEAD.value])
    def patch(self, request, record_id):
        record = self._get_record(record_id)
        if not record:
            return CustomResponse(
                general_message='Inspiration Station episode not found.'
            ).get_failure_response()

        serializer = InspirationStationWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return CustomResponse(
                general_message='Invalid data.',
                message=serializer.errors,
            ).get_failure_response()

        user_id = JWTUtils.fetch_user_id(request)
        data = serializer.validated_data
        data.pop('content_type', None)

        for attr, value in data.items():
            setattr(record, attr, value)
        record.updated_by_id = user_id
        record.save()

        return CustomResponse(
            general_message='Inspiration Station episode updated.',
            response=InspirationStationReadSerializer(record).data,
        ).get_success_response()

    @extend_schema(tags=['Media Content - Inspiration Station'])
    @RoleRequired([RoleType.ADMIN.value, RoleType.ASSOCIATE.value, RoleType.IG_LEAD.value])
    def delete(self, request, record_id):
        record = self._get_record(record_id)
        if not record:
            return CustomResponse(
                general_message='Inspiration Station episode not found.'
            ).get_failure_response()

        record.deleted_at = timezone.now()
        record.updated_by_id = JWTUtils.fetch_user_id(request)
        record.save(update_fields=['deleted_at', 'updated_by_id'])

        return CustomResponse(
            general_message='Inspiration Station episode deleted.'
        ).get_success_response()
