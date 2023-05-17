from functools import partial
import uuid
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView

from db.user import User
from utils.permission import CustomizePermission, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils, DateTimeUtils

from .dash_user_serializer import UserDashboardSerializer

from django.db import IntegrityError


class UserAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_queryset = User.objects.all()
        queryset = CommonUtils.get_paginated_queryset(
            user_queryset,
            request,
            [
                "id",
                "discord_id",
                "mu_id",
                "first_name",
                "last_name",
                "email",
                "mobile",
                "gender",
                "dob",
                "admin",
                "active",
                "exist_in_guild",
                "created_at",
                "total_karma",
            ],
        )

        serializer = UserDashboardSerializer(queryset, many=True)
        return CustomResponse(
            response={"users": serializer.data}
        ).get_success_response()

    @RoleRequired(
        roles=[
            RoleType.ADMIN,
        ]
    )
    def patch(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
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

    @RoleRequired(
        roles=[
            RoleType.ADMIN,
        ]
    )
    def delete(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        user.delete()
        return CustomResponse().get_success_response()
