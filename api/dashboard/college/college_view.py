from rest_framework.views import APIView
from utils.types import OrganizationType, RoleType
from db.organization import College, Organization
from db.user import User
from utils.permission import JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils
from django.db.models import Case, When, CharField, F
from .serializer import CollegeListSerializer

class CollegeApi(APIView):
    def get(self, request, college_code=None):
        colleges = Organization.objects.filter(
            org_type=OrganizationType.COLLEGE.value
        ).select_related(
            "created_by",
            "updated_by",
            "affiliation",
            "district",
        )
        if college_code:
            colleges = colleges.filter(code=college_code)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            colleges,
            request,
            search_fields=[""],
            sort_fields=None,
        )
        serializer = CollegeListSerializer(
            paginated_queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )
