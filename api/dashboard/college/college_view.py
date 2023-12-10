from rest_framework.views import APIView

from db.organization import College
from utils.response import CustomResponse
from utils.utils import CommonUtils
from .serializer import (
    CollegeListSerializer,
)


class CollegeApi(APIView):
    def get(self, request, college_code=None):
        if college_code:
            colleges = College.objects.filter(id=college_code)
        else:
            colleges = College.objects.all().select_related("org")

        paginated_queryset = CommonUtils.get_paginated_queryset(
            colleges,
            request,
            search_fields=["org",],
            sort_fields=None,
        )
        serializer = CollegeListSerializer(
            paginated_queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )
