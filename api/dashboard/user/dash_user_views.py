from rest_framework.views import APIView

from db.user import User
from utils.response import CustomResponse
from utils.utils import CommonUtils

from .dash_user_serializer import UserDashboardSerializer


class UserAPI(APIView):
    FIELDS = [
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
    ]

    def get(self, request):
        
        queryset = User.objects.all()
        # queryset = CommonUtils.get_paginated_queryset(queryset, request, self.FIELDS)
        serializer = UserDashboardSerializer(queryset, many=True)
        serialized_data = serializer.data

        return CustomResponse(
            response={"users": serialized_data}
        ).get_success_response()
