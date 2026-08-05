"""
Community Partner API views.

Exposes CRUD endpoints for CommunityPartner, with IG links managed via a
plain `interest_groups` id list embedded in the create/update payload
(mirroring api/dashboard/media_content's `_sync_ig_links` approach) rather
than a separate link/unlink endpoint.

Read (GET) endpoints are publicly accessible.
Write (POST / PATCH / DELETE) endpoints require ADMIN / ASSOCIATE / IG_LEAD.
"""
import uuid

from rest_framework.views import APIView

from db.community_partner import CommunityPartner, IgCommunityPartnerLink
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils

from .serializers import CommunityPartnerReadSerializer, CommunityPartnerWriteSerializer

from drf_spectacular.utils import extend_schema


class PublicGetMixin:
    """Mixin to bypass JWT authentication for GET requests."""
    def get_authenticators(self):
        if getattr(self, 'request', None) and self.request.method == 'GET':
            return []
        return super().get_authenticators()


def _sync_ig_links(record, ig_ids, user_id):
    """Replace all IgCommunityPartnerLink rows for `record` with one per id
    in `ig_ids`."""
    record.ig_links.all().delete()
    ig_ids = ig_ids or []
    IgCommunityPartnerLink.objects.bulk_create([
        IgCommunityPartnerLink(
            id=str(uuid.uuid4()),
            community_partner=record,
            interest_group_id=ig_id,
            created_by_id=user_id,
        )
        for ig_id in ig_ids
    ])


class CommunityPartnerListCreateAPI(PublicGetMixin, APIView):
    """
    GET  /community-partner/  — Public paginated list of community partners.
                                 Optional `?ig_id=<id>` filters to partners
                                 linked to that Interest Group.
    POST /community-partner/  — Create a community partner (Admin/Associate/IG Lead).
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Community Partner'])
    def get(self, request):
        qs = CommunityPartner.objects.all().order_by('name')

        ig_id = request.query_params.get('ig_id')
        if ig_id:
            partner_ids = IgCommunityPartnerLink.objects.filter(
                interest_group_id=ig_id
            ).values_list('community_partner_id', flat=True)
            qs = qs.filter(id__in=partner_ids)

        paginated = CommonUtils.get_paginated_queryset(
            qs, request,
            search_fields=['name'],
            sort_fields={
                'name': 'name',
                'created_at': 'created_at',
            },
        )

        serializer = CommunityPartnerReadSerializer(paginated['queryset'], many=True)
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )

    @extend_schema(tags=['Community Partner'])
    @RoleRequired([RoleType.ADMIN.value, RoleType.ASSOCIATE.value, RoleType.IG_LEAD.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        serializer = CommunityPartnerWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                general_message='Invalid data.',
                message=serializer.errors,
            ).get_failure_response()

        data = serializer.validated_data
        ig_ids = data.pop('interest_groups', None)
        record = CommunityPartner.objects.create(
            id=str(uuid.uuid4()),
            created_by_id=user_id,
            updated_by_id=user_id,
            **data,
        )

        _sync_ig_links(record, ig_ids, user_id)

        return CustomResponse(
            general_message='Community partner created successfully.',
            response=CommunityPartnerReadSerializer(record).data,
        ).get_success_response()


class CommunityPartnerDetailAPI(PublicGetMixin, APIView):
    """
    GET    /community-partner/<partner_id>/  — Public partner detail.
    PATCH  /community-partner/<partner_id>/  — Partial update (Admin/Associate/IG Lead).
    DELETE /community-partner/<partner_id>/  — Delete (Admin/Associate/IG Lead).
    """
    authentication_classes = [CustomizePermission]

    def _get_record(self, partner_id):
        return CommunityPartner.objects.filter(id=partner_id).first()

    @extend_schema(tags=['Community Partner'])
    def get(self, request, partner_id):
        record = self._get_record(partner_id)
        if not record:
            return CustomResponse(
                general_message='Community partner not found.'
            ).get_failure_response()

        return CustomResponse(
            general_message='Community partner retrieved.',
            response=CommunityPartnerReadSerializer(record).data,
        ).get_success_response()

    @extend_schema(tags=['Community Partner'])
    @RoleRequired([RoleType.ADMIN.value, RoleType.ASSOCIATE.value, RoleType.IG_LEAD.value])
    def patch(self, request, partner_id):
        record = self._get_record(partner_id)
        if not record:
            return CustomResponse(
                general_message='Community partner not found.'
            ).get_failure_response()

        serializer = CommunityPartnerWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return CustomResponse(
                general_message='Invalid data.',
                message=serializer.errors,
            ).get_failure_response()

        user_id = JWTUtils.fetch_user_id(request)
        data = serializer.validated_data

        if 'interest_groups' in data:
            ig_ids = data.pop('interest_groups')
            _sync_ig_links(record, ig_ids, user_id)

        for attr, value in data.items():
            setattr(record, attr, value)
        record.updated_by_id = user_id
        record.save()

        return CustomResponse(
            general_message='Community partner updated.',
            response=CommunityPartnerReadSerializer(record).data,
        ).get_success_response()

    @extend_schema(tags=['Community Partner'])
    @RoleRequired([RoleType.ADMIN.value, RoleType.ASSOCIATE.value, RoleType.IG_LEAD.value])
    def delete(self, request, partner_id):
        record = self._get_record(partner_id)
        if not record:
            return CustomResponse(
                general_message='Community partner not found.'
            ).get_failure_response()

        record.delete()

        return CustomResponse(
            general_message='Community partner deleted.'
        ).get_success_response()
