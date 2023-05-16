# This is a Django REST API view that retrieves a paginated list of users and returns it as a
# serialized response.
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from rest_framework.views import APIView

from db.user import User
from utils.response import CustomResponse
from .dash_user_serializer import UserDashboardSerializer
from utils.utils import CommonUtils


class UserAPI(APIView):

    def get(self, request):
        user_queryset = User.objects.all()
        
        queryset = CommonUtils.get_paginated_queryset(
            user_queryset, request, ["id", "first_name"]
        )
        
        serializer = UserDashboardSerializer(queryset, many=True)
        serialized_data = serializer.data

        return CustomResponse(
            response={"users": serialized_data}
        ).get_success_response()
        
        
    