import contextlib
import uuid
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

from db.user import User, UserRoleLink, Role
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils, DateTimeUtils
from .dash_user_serializer import UserDashboardSerializer


class UserAPI(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.ADMIN])
    def get(self, request):
        user_queryset = User.objects.all()
        queryset = CommonUtils.get_paginated_queryset(
            user_queryset,
            request,
            ["mu_id", "first_name", "last_name", "email", "mobile"],
        )
        serializer = UserDashboardSerializer(queryset.get("queryset"), many=True)

        return CustomResponse(
            response={
                "users": serializer.data,
                "pagination": queryset.get("pagination"),
            }
        ).get_success_response()

    @RoleRequired(roles=[RoleType.ADMIN])
    def patch(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        roles = request.data.get("roles", [])
        admin_id = JWTUtils.fetch_user_id(request)

        UserRoleLink.objects.filter(user=user).delete()

        for role_title in roles:
            with contextlib.suppress(Role.DoesNotExist):
                role = Role.objects.get(title=role_title)
                user_role_link = UserRoleLink.objects.create(
                    id=uuid.uuid4(),
                    user=user,
                    role=role,
                    verified=True,
                    created_by=admin_id,
                    created_at=DateTimeUtils.get_current_utc_time(),
                )
                user_role_link.save()

        serializer = UserDashboardSerializer(user, data=request.data, partial=True)

        if not serializer.is_valid():
            return CustomResponse(
                response={"users": serializer.errors}
            ).get_failure_response()
        try:
            serializer.save()
            return CustomResponse(
                response={"users": serializer.data}
            ).get_success_response()

        except IntegrityError as e:
            return CustomResponse(response={"users": str(e)}).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN])
    def delete(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        user.delete()
        return CustomResponse().get_success_response()
