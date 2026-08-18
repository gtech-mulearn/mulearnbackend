"""
Media Content API views.

Exposes CRUD endpoints for the content types backed by the
single ``MediaContent`` model:

  - Office Hours           → /media-content/office-hours/
  - Salt Mango Tree        → /media-content/salt-mango-tree/
  - Inspiration Station    → /media-content/inspiration-station/
  - Grab Your Superpowers  → /media-content/grab-your-superpowers/

Read (GET) endpoints are publicly accessible.
Write (POST / PATCH / DELETE) endpoints require the ADMIN role.
"""
import uuid

from django.utils import timezone
from rest_framework.views import APIView

from db.events import MediaContent, IgMediaContentLink
from db.task import InterestGroup
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
import csv
import codecs

from .serializers import (
    OfficeHoursReadSerializer,
    OfficeHoursWriteSerializer,
    SaltMangoTreeReadSerializer,
    SaltMangoTreeWriteSerializer,
    InspirationStationReadSerializer,
    InspirationStationWriteSerializer,
    GrabYourSuperpowersReadSerializer,
    GrabYourSuperpowersWriteSerializer,
)
from api.dashboard.media_content.image_utils import (
    merge_media_write_payload,
    delete_stale_media,
)
from mu_celery.media_content_tasks import fetch_and_attach_poster

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
    from django.db.models import Q

    # Accepts repeated params (?status=a&status=b) and/or comma-separated
    # values (?status=a,b) — both are normalized into one status list.
    raw_statuses = params.getlist('status')
    statuses = {
        s.strip().lower()
        for raw in raw_statuses
        for s in raw.split(',')
        if s.strip()
    }

    if statuses:
        status_q = Q()
        if 'upcoming' in statuses:
            status_q |= Q(date__gt=date.today())
        if 'ongoing' in statuses:
            status_q |= Q(date=date.today())
        if 'completed' in statuses:
            status_q |= Q(date__lt=date.today())
        if status_q:
            qs = qs.filter(status_q)

    if has_zone:
        if zone := params.get('zone'):
            qs = qs.filter(zone=zone)

    return qs


def _sync_ig_links(record, ig_ids):
    """Replace all IgMediaContentLink rows for `record` with one per id in
    `ig_ids`, and return the new link ids (to store on record.interest_groups).
    """
    record.ig_links.all().delete()
    ig_ids = ig_ids or []
    links = IgMediaContentLink.objects.bulk_create([
        IgMediaContentLink(
            id=str(uuid.uuid4()),
            media_content=record,
            interest_group_id=ig_id,
        )
        for ig_id in ig_ids
    ])
    return [link.id for link in links]


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

        serializer = OfficeHoursReadSerializer(paginated['queryset'], many=True, context={'request': request})
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )


    @extend_schema(tags=['Media Content - Office Hours'])
    @RoleRequired([
        RoleType.ADMIN.value,
        RoleType.ASSOCIATE.value,
        RoleType.IG_LEAD.value,
        RoleType.ZONAL_CAMPUS_LEAD.value,
        RoleType.DISTRICT_CAMPUS_LEAD.value,
    ])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        payload, merge_error, pending_urls = merge_media_write_payload(
            request, partial=False, skip_remote_fetch=True
        )
        if merge_error:
            return CustomResponse(
                general_message=merge_error,
            ).get_failure_response()

        serializer = OfficeHoursWriteSerializer(data=payload)
        if not serializer.is_valid():
            return CustomResponse(
                general_message='Invalid data.',
                message=serializer.errors,
            ).get_failure_response()

        data = serializer.validated_data
        ig_ids = data.pop('interest_groups', None)
        record = MediaContent.objects.create(
            id=str(uuid.uuid4()),
            created_by_id=user_id,
            updated_by_id=user_id,
            **data,
        )

        link_ids = _sync_ig_links(record, ig_ids)
        record.interest_groups = link_ids
        record.save(update_fields=['interest_groups'])

        for field, (raw_url, subdir) in pending_urls.items():
            fetch_and_attach_poster.delay(record.id, raw_url, subdir, field)

        return CustomResponse(
            general_message='Office Hours session created successfully.',
            response=OfficeHoursReadSerializer(record, context={'request': request}).data,
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

        serializer = OfficeHoursReadSerializer(record, context={'request': request})
        return CustomResponse(
            general_message='Office Hours session retrieved.',
            response=serializer.data,
        ).get_success_response()


    @extend_schema(tags=['Media Content - Office Hours'])
    @RoleRequired([
        RoleType.ADMIN.value,
        RoleType.ASSOCIATE.value,
        RoleType.IG_LEAD.value,
        RoleType.ZONAL_CAMPUS_LEAD.value,
        RoleType.DISTRICT_CAMPUS_LEAD.value,
    ])
    def patch(self, request, record_id):
        record = self._get_record(record_id)
        if not record:
            return CustomResponse(
                general_message='Office Hours session not found.'
            ).get_failure_response()

        payload, merge_error, pending_urls = merge_media_write_payload(
            request, partial=True, skip_remote_fetch=True
        )
        if merge_error:
            return CustomResponse(
                general_message=merge_error,
            ).get_failure_response()

        serializer = OfficeHoursWriteSerializer(data=payload, partial=True)
        if not serializer.is_valid():
            return CustomResponse(
                general_message='Invalid data.',
                message=serializer.errors,
            ).get_failure_response()

        user_id = JWTUtils.fetch_user_id(request)
        data = serializer.validated_data
        data.pop('content_type', None)  # never allow overriding the discriminator

        if 'interest_groups' in data:
            ig_ids = data.pop('interest_groups')
            data['interest_groups'] = _sync_ig_links(record, ig_ids)

        old_poster = record.poster_thumbnail
        for attr, value in data.items():
            setattr(record, attr, value)
        record.updated_by_id = user_id
        record.save()

        # Only delete the old file when its replacement is already in hand
        # (i.e. the field was resolved synchronously via a direct upload or
        # an already-relative path).  For deferred URL fields the old path is
        # forwarded to the Celery task, which removes it *after* the new file
        # is confirmed written — preventing unrecoverable data loss if the
        # task exhausts its retries.
        poster_field_deferred = 'poster_thumbnail' in pending_urls
        if not poster_field_deferred:
            delete_stale_media(old_poster, record.poster_thumbnail)

        for field, (raw_url, subdir) in pending_urls.items():
            field_old_path = old_poster if field == 'poster_thumbnail' else None
            fetch_and_attach_poster.delay(record.id, raw_url, subdir, field, field_old_path)

        return CustomResponse(
            general_message='Office Hours session updated.',
            response=OfficeHoursReadSerializer(record, context={'request': request}).data,
        ).get_success_response()



    @extend_schema(tags=['Media Content - Office Hours'])
    @RoleRequired([
        RoleType.ADMIN.value,
        RoleType.ASSOCIATE.value,
        RoleType.IG_LEAD.value,
        RoleType.ZONAL_CAMPUS_LEAD.value,
        RoleType.DISTRICT_CAMPUS_LEAD.value,
    ])
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
    @RoleRequired([
        RoleType.ADMIN.value,
        RoleType.ASSOCIATE.value,
        RoleType.IG_LEAD.value,
        RoleType.ZONAL_CAMPUS_LEAD.value,
        RoleType.DISTRICT_CAMPUS_LEAD.value,
    ])
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
    @RoleRequired([
        RoleType.ADMIN.value,
        RoleType.ASSOCIATE.value,
        RoleType.IG_LEAD.value,
        RoleType.ZONAL_CAMPUS_LEAD.value,
        RoleType.DISTRICT_CAMPUS_LEAD.value,
    ])
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
    @RoleRequired([
        RoleType.ADMIN.value,
        RoleType.ASSOCIATE.value,
        RoleType.IG_LEAD.value,
        RoleType.ZONAL_CAMPUS_LEAD.value,
        RoleType.DISTRICT_CAMPUS_LEAD.value,
    ])
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
    @RoleRequired([
        RoleType.ADMIN.value,
        RoleType.ASSOCIATE.value,
        RoleType.IG_LEAD.value,
        RoleType.ZONAL_CAMPUS_LEAD.value,
        RoleType.DISTRICT_CAMPUS_LEAD.value,
    ])
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
    @RoleRequired([
        RoleType.ADMIN.value,
        RoleType.ASSOCIATE.value,
        RoleType.IG_LEAD.value,
        RoleType.ZONAL_CAMPUS_LEAD.value,
        RoleType.DISTRICT_CAMPUS_LEAD.value,
    ])
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
    @RoleRequired([
        RoleType.ADMIN.value,
        RoleType.ASSOCIATE.value,
        RoleType.IG_LEAD.value,
        RoleType.ZONAL_CAMPUS_LEAD.value,
        RoleType.DISTRICT_CAMPUS_LEAD.value,
    ])
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


# ─────────────────────────────────────────────────────────────────────────────
# Grab Your Superpowers
# ─────────────────────────────────────────────────────────────────────────────

class GrabYourSuperpowersListCreateAPI(PublicGetMixin, APIView):
    """
    GET  /media-content/grab-your-superpowers/  — Public paginated list of sessions.
    POST /media-content/grab-your-superpowers/  — Create a session (Admin only).
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Media Content - Grab Your Superpowers'])
    def get(self, request):
        qs = _base_qs(MediaContent.ContentType.GRAB_YOUR_SUPERPOWERS)
        qs = _apply_common_filters(qs, request, has_zone=False)

        paginated = CommonUtils.get_paginated_queryset(
            qs, request,
            search_fields=['title', 'performer', 'campus', 'description'],
            sort_fields={
                'date': 'date',
                'campus': 'campus',
                'created_at': 'created_at',
            },
        )

        serializer = GrabYourSuperpowersReadSerializer(paginated['queryset'], many=True)
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )

    @extend_schema(tags=['Media Content - Grab Your Superpowers'])
    @RoleRequired([
        RoleType.ADMIN.value,
        RoleType.ASSOCIATE.value,
        RoleType.IG_LEAD.value,
        RoleType.ZONAL_CAMPUS_LEAD.value,
        RoleType.DISTRICT_CAMPUS_LEAD.value,
    ])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = GrabYourSuperpowersWriteSerializer(data=request.data)
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
            general_message='Grab Your Superpowers session created successfully.',
            response=GrabYourSuperpowersReadSerializer(record).data,
        ).get_success_response()


class GrabYourSuperpowersDetailAPI(PublicGetMixin, APIView):
    """
    GET    /media-content/grab-your-superpowers/<record_id>/
    PATCH  /media-content/grab-your-superpowers/<record_id>/  (Admin)
    DELETE /media-content/grab-your-superpowers/<record_id>/  (Admin)
    """
    authentication_classes = [CustomizePermission]

    def _get_record(self, record_id):
        return MediaContent.objects.filter(
            id=record_id,
            content_type=MediaContent.ContentType.GRAB_YOUR_SUPERPOWERS,
            deleted_at__isnull=True,
        ).first()

    @extend_schema(tags=['Media Content - Grab Your Superpowers'])
    def get(self, request, record_id):
        record = self._get_record(record_id)
        if not record:
            return CustomResponse(
                general_message='Grab Your Superpowers session not found.'
            ).get_failure_response()

        return CustomResponse(
            general_message='Grab Your Superpowers session retrieved.',
            response=GrabYourSuperpowersReadSerializer(record).data,
        ).get_success_response()

    @extend_schema(tags=['Media Content - Grab Your Superpowers'])
    @RoleRequired([
        RoleType.ADMIN.value,
        RoleType.ASSOCIATE.value,
        RoleType.IG_LEAD.value,
        RoleType.ZONAL_CAMPUS_LEAD.value,
        RoleType.DISTRICT_CAMPUS_LEAD.value,
    ])
    def patch(self, request, record_id):
        record = self._get_record(record_id)
        if not record:
            return CustomResponse(
                general_message='Grab Your Superpowers session not found.'
            ).get_failure_response()

        serializer = GrabYourSuperpowersWriteSerializer(data=request.data, partial=True)
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
            general_message='Grab Your Superpowers session updated.',
            response=GrabYourSuperpowersReadSerializer(record).data,
        ).get_success_response()

    @extend_schema(tags=['Media Content - Grab Your Superpowers'])
    @RoleRequired([
        RoleType.ADMIN.value,
        RoleType.ASSOCIATE.value,
        RoleType.IG_LEAD.value,
        RoleType.ZONAL_CAMPUS_LEAD.value,
        RoleType.DISTRICT_CAMPUS_LEAD.value,
    ])
    def delete(self, request, record_id):
        record = self._get_record(record_id)
        if not record:
            return CustomResponse(
                general_message='Grab Your Superpowers session not found.'
            ).get_failure_response()

        record.deleted_at = timezone.now()
        record.updated_by_id = JWTUtils.fetch_user_id(request)
        record.save(update_fields=['deleted_at', 'updated_by_id'])

        return CustomResponse(
            general_message='Grab Your Superpowers session deleted.'
        ).get_success_response()


class MediaContentBulkImportAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Media Content - Import'])
    @RoleRequired([
        RoleType.ADMIN.value,
        RoleType.ASSOCIATE.value,
        RoleType.IG_LEAD.value,
        RoleType.ZONAL_CAMPUS_LEAD.value,
        RoleType.DISTRICT_CAMPUS_LEAD.value,
    ])
    def post(self, request):
        file = request.data.get('file')
        if not file:
            return CustomResponse(
                general_message='File is required.',
            ).get_failure_response()

        ALLOWED_CSV_MIME_TYPES = {'text/csv', 'application/csv', 'application/vnd.ms-excel'}
        if file.content_type not in ALLOWED_CSV_MIME_TYPES:
            return CustomResponse(
                general_message='Invalid file type. Please upload a CSV file.',
            ).get_failure_response()

       
        try:
            reader = csv.DictReader(codecs.iterdecode(file, 'utf-8-sig'))
            rows = list(reader)  # materialize here so decode errors are caught
        except Exception:
            return CustomResponse(
                general_message='Error reading CSV file. Ensure it is UTF-8 encoded.',
            ).get_failure_response()

        if not rows:
            return CustomResponse(
                general_message='CSV file is empty. No records to import.',
            ).get_failure_response()

        user_id = JWTUtils.fetch_user_id(request)
        success_count = 0
        failed_rows = []

        for row_num, row in enumerate(rows, start=2):
            content_type = row.get('content_type', '').strip()
            row_data = dict(row)

            # Clean up empty values to avoid validation issues
            row_data = {k: v for k, v in row_data.items() if v is not None and str(v).strip() != ''}

            if content_type == MediaContent.ContentType.OFFICE_HOURS:
                # Normalize: CSV may use 'topic' instead of 'title'
                if 'topic' in row_data and not row_data.get('title'):
                    row_data['title'] = row_data.pop('topic')
                if 'interest_groups' in row_data:
                    # CSV supplies human-readable IG names; resolve to ids
                    # (the write serializer expects interest_group ids).
                    names = [
                        ig.strip()
                        for ig in str(row_data['interest_groups']).split(',')
                        if ig.strip()
                    ]
                    ig_by_name = dict(
                        InterestGroup.objects.filter(name__in=names).values_list('name', 'id')
                    )
                    unknown_names = [n for n in names if n not in ig_by_name]
                    if unknown_names:
                        failed_rows.append({
                            "row": row_num,
                            "title": row.get('title') or row.get('topic', ''),
                            "reason": f"Unknown interest group name(s): {', '.join(unknown_names)}.",
                        })
                        continue
                    row_data['interest_groups'] = [ig_by_name[n] for n in names]
                serializer = OfficeHoursWriteSerializer(data=row_data)

            elif content_type == MediaContent.ContentType.SALT_MANGO_TREE:
                # Normalize: CSV may use 'title' instead of 'topic'
                if 'title' in row_data and not row_data.get('topic'):
                    row_data['topic'] = row_data.pop('title')
                serializer = SaltMangoTreeWriteSerializer(data=row_data)

            elif content_type == MediaContent.ContentType.INSPIRATION_STATION:
                # Normalize: CSV may use 'title' instead of 'topic'
                if 'title' in row_data and not row_data.get('topic'):
                    row_data['topic'] = row_data.pop('title')
                serializer = InspirationStationWriteSerializer(data=row_data)

            elif content_type == MediaContent.ContentType.GRAB_YOUR_SUPERPOWERS:
                serializer = GrabYourSuperpowersWriteSerializer(data=row_data)

            else:
                failed_rows.append({
                    "row": row_num,
                    "title": row.get('title') or row.get('topic', ''),
                    "reason": (
                        f"Invalid or missing content_type: '{content_type}'. "
                        "Must be 'office_hours', 'salt_mango_tree', 'inspiration_station', "
                        "or 'grab_your_superpowers'."
                    ),
                })
                continue

            if serializer.is_valid():
                data = serializer.validated_data
                ig_ids = data.pop('interest_groups', None)
                record = MediaContent.objects.create(
                    id=str(uuid.uuid4()),
                    created_by_id=user_id,
                    updated_by_id=user_id,
                    **data,
                )
                if content_type == MediaContent.ContentType.OFFICE_HOURS:
                    record.interest_groups = _sync_ig_links(record, ig_ids)
                    record.save(update_fields=['interest_groups'])
                success_count += 1
            else:
                failed_rows.append({
                    "row": row_num,
                    "title": row.get('title') or row.get('topic', ''),
                    "reason": serializer.errors,
                })

        return CustomResponse(
            general_message='Bulk import completed.',
            response={
                'success_count': success_count,
                'failed_count': len(failed_rows),
                'failed_rows': failed_rows,
            }
        ).get_success_response()


class MediaContentBulkExportAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Media Content - Export'])
    @RoleRequired([
        RoleType.ADMIN.value,
        RoleType.ASSOCIATE.value,
        RoleType.IG_LEAD.value,
        RoleType.ZONAL_CAMPUS_LEAD.value,
        RoleType.DISTRICT_CAMPUS_LEAD.value,
    ])
    def get(self, request, content_type):
        if content_type == MediaContent.ContentType.OFFICE_HOURS:
            queryset = MediaContent.objects.filter(
                content_type=MediaContent.ContentType.OFFICE_HOURS,
                deleted_at__isnull=True,
            )
            serializer = OfficeHoursReadSerializer(queryset, many=True, context={'request': request})
        elif content_type == MediaContent.ContentType.SALT_MANGO_TREE:
            queryset = MediaContent.objects.filter(
                content_type=MediaContent.ContentType.SALT_MANGO_TREE,
                deleted_at__isnull=True,
            )
            serializer = SaltMangoTreeReadSerializer(queryset, many=True)
        elif content_type == MediaContent.ContentType.INSPIRATION_STATION:
            queryset = MediaContent.objects.filter(
                content_type=MediaContent.ContentType.INSPIRATION_STATION,
                deleted_at__isnull=True,
            )
            serializer = InspirationStationReadSerializer(queryset, many=True)
        elif content_type == MediaContent.ContentType.GRAB_YOUR_SUPERPOWERS:
            queryset = MediaContent.objects.filter(
                content_type=MediaContent.ContentType.GRAB_YOUR_SUPERPOWERS,
                deleted_at__isnull=True,
            )
            serializer = GrabYourSuperpowersReadSerializer(queryset, many=True)
        else:
            return CustomResponse(
                general_message='Invalid content type. Must be office_hours, salt_mango_tree, '
                                 'inspiration_station, or grab_your_superpowers.'
            ).get_failure_response()

        return CommonUtils.generate_csv(serializer.data, f"{content_type}_export")
        

        
