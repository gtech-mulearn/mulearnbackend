import uuid
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView

from db.user import User
from utils.permission import CustomizePermission, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils, DateTimeUtils

from .dash_user_serializer import UserDashboardSerializer


class UserAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_queryset = User.objects.all()

        queryset = CommonUtils.get_paginated_queryset(
            user_queryset, request, ["id", "first_name"]
        )

        serializer = UserDashboardSerializer(queryset, many=True)

        return CustomResponse(
            response={"users": serializer.data}
        ).get_success_response()



