"""
Partner admin views — endpoints 7–8.
Restricted to Admins role.
"""
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from db.partner import UserPartner
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils

from . import serializers


class PartnerAdminListAPI(APIView):
    """
    GET /partner/admin/list/
    List all partner registrations with optional status filter.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Partner Admin"],
        description="List all partner registrations. Admins use this to review pending registrations.",
        responses={200: serializers.PartnerListSerializer(many=True)},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        partners = UserPartner.objects.select_related("user_link").all()

        status_filter = request.query_params.get("status")
        if status_filter:
            partners = partners.filter(status=status_filter)

        paginated = CommonUtils.get_paginated_queryset(
            partners, request,
            search_fields=["name", "email", "partner_type", "location"],
            sort_fields={
                "name": "name",
                "status": "status",
                "submitted_at": "-submitted_at",
            },
        )

        serializer = serializers.PartnerListSerializer(paginated["queryset"], many=True)
        return CustomResponse(
            general_message="Partner list fetched successfully.",
            response={
                "data": serializer.data,
                "pagination": paginated["pagination"],
            },
        ).get_success_response()


class PartnerAdminVerifyAPI(APIView):
    """
    PATCH /partner/admin/<partner_id>/verify/
    Approve or reject a partner registration.
    On approval assigns the Partner role to the registering user.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Partner Admin"],
        description="Approve or reject a partner registration.",
        request=serializers.PartnerVerifySerializer,
    )
    @role_required([RoleType.ADMIN.value])
    def patch(self, request, partner_id):
        user_id = JWTUtils.fetch_user_id(request)
        partner = UserPartner.objects.select_related("user_link").filter(id=partner_id).first()

        if not partner:
            return CustomResponse(
                general_message="Partner not found."
            ).get_failure_response(status_code=404)

        if partner.status == "verified":
            return CustomResponse(
                general_message="Partner is already verified."
            ).get_failure_response()

        serializer = serializers.PartnerVerifySerializer(
            partner, data=request.data, context={"user_id": user_id}
        )
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        serializer.save()
        return CustomResponse(
            general_message=f"Partner status updated to {serializer.validated_data['status']} successfully.",
            response={
                "id": partner.id,
                "name": partner.name,
                "status": partner.status,
                "verified_at": partner.verified_at,
                "rejection_reason": partner.rejection_reason,
            },
        ).get_success_response()
