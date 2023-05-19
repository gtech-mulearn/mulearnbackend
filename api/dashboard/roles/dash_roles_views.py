import uuid

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

from db.user import Role
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils, DateTimeUtils
from .dash_roles_serializer import RoleDashboardSerializer


class RoleAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        roles_queryset = Role.objects.all()
        queryset = CommonUtils.get_paginated_queryset(roles_queryset, request, ["id", "title"])

        serializer = RoleDashboardSerializer(queryset, many=True)
        return CustomResponse(
            response={"roles": serializer.data}
        ).get_success_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def patch(self, request, roles_id):
        user_id = JWTUtils.fetch_user_id(request)
        role = Role.objects.filter(id=roles_id).first()
        print(role.id, role.title, role.description)

        role.title = request.data.get('title')
        role.description = request.data.get('description')
        role.updated_by_id = user_id
        role.updated_at = DateTimeUtils.get_current_utc_time()
        role.save()

        return CustomResponse(
            general_message=f"{role.title} updated successfully"
        ).get_success_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def delete(self, request, roles_id):
        role = get_object_or_404(Role, id=roles_id)
        role.delete()
        return CustomResponse(general_message="Role deleted successfully").get_success_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        role_data = Role.objects.create(
            id=uuid.uuid4(),
            title=request.data.get('title'),
            description=request.data.get('description'),
            updated_by_id=user_id,
            updated_at=DateTimeUtils.get_current_utc_time(),
            created_by_id=user_id,
            created_at=DateTimeUtils.get_current_utc_time()
        )
        serializer = RoleDashboardSerializer(role_data)
        return CustomResponse(
            response={"roles": serializer.data}
        ).get_success_response()
