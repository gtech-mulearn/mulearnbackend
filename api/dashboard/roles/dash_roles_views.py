from rest_framework.views import APIView

from db.user import Role
from utils.response import CustomResponse

# all roles management or user role management?
# list existing roles
# create new role
# edit user role    
# delete user role
# get role of a specific user

ALL_FIELDS = {
    "id",
    "title",
    "description",
    "updated_by",
    "updated_at",
    "created_by",
    "verified",
    "created_at",
}

from django.shortcuts import get_object_or_404

from rest_framework.views import APIView

from db.user import User
from utils.permission import CustomizePermission, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils

from .dash_user_serializer import UserDashboardSerializer

from django.db import IntegrityError


class RolesAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        roles_queryset = Roles.objects.all()
        queryset = CommonUtils.get_paginated_queryset(
            roles_queryset,
            request,
            [
                "id",
                "title",
                "description",
                "updated_by",
                "updated_at",
                "created_by",
                "verified",
                "created_at",
            ],
        )

        serializer = RolesDashboardSerializer(queryset, many=True)
        return CustomResponse(
            response={"roles": serializer.data}
        ).get_success_response()

    @RoleRequired(roles=[RoleType.ADMIN,])
    def patch(self, request, user_id):
        roles = get_object_or_404(Roles, id=roles_id)
        serializer = RolesDashboardSerializer(roles, data=request.data, partial=True)

        if not serializer.is_valid():
            return CustomResponse(
                response={"roles": serializer.errors}
            ).get_failure_response()
        try:
            serializer.save()
            return CustomResponse(
                response={"roles": serializer.data}
            ).get_success_response()

        except IntegrityError as e:
            return CustomResponse(response={"roles": str(e)}).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN,])
    def delete(self, request, roles_id):
        roles = get_object_or_404(Roles, id=roles_id)
        roles.delete()
        return CustomResponse().get_success_response()

