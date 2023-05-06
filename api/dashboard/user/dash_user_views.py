from rest_framework.views import APIView

from api.user.serializers import (
    OrgSerializer,
)
from db.organization import Organization
from db.user import User
from utils.response import CustomResponse
from utils.types import OrganizationType
from utils.utils import CommonUtils

ALL_FIELDS = {
    "id": "id",
    "discord_id": "discord_id",
    "mu_id": "mu_id",
    "first_name": "first_name",
    "last_name": "last_name",
    "email": "email",
    "mobile": "mobile",
    "gender": "gender",
    "dob": "dob",
    "admin": "admin",
    "active": "active",
    "exist_in_guild": "exist_in_guild",
    "created_at": "created_at",
    "github_username": "github__username",
    "karma": "totalkarma__karma",
}

FIELD_NAMES, FIELD_VALUES = zip(*ALL_FIELDS.items())

FIELD_LENGTH = len(ALL_FIELDS)

DEFAULT_FIELDS = ["discord_id", "first_name", "last_name", "active", "karma"]

MAX_COLUMNS = 5


class CollegePaginationTestAPI(APIView):

    def get(self, request):
        org_queryset = Organization.objects.filter(org_type=OrganizationType.COLLEGE.value)
        paginated_queryset = CommonUtils.get_paginated_queryset(org_queryset, request, ['title', 'id'])
        college_serializer_data = OrgSerializer(paginated_queryset, many=True).data
        return CustomResponse(response={"colleges": college_serializer_data}).get_success_response()


class UserAPI(APIView):
    def get(self, request):
        selected_columns = request.GET.get("fields", "").split(",")

        users = User.objects.select_related("github").prefetch_related("totalkarma")

        if (len(selected_columns) != MAX_COLUMNS) and (
                any(field not in ALL_FIELDS for field in selected_columns)
        ):
            selected_columns = DEFAULT_FIELDS

        for field in selected_columns:
            try:
                selected_columns[selected_columns.index(field)] = ALL_FIELDS[field]
            except KeyError:
                pass

        users = users.values(*selected_columns)

        user_dicts = [
            {
                selected_columns[i]: user[selected_columns[i]]
                if selected_columns[i] in user
                else None
                for i in range(MAX_COLUMNS)
            }
            for user in users
        ]

        user_dicts = normalize(user_dicts)
        print(user_dicts)

        return CustomResponse(
            general_message={"columns": FIELD_NAMES, "len_columns": FIELD_LENGTH},
            response=user_dicts,
        ).get_success_response()


def normalize(api: list) -> list:
    for item in api:
        for key, value in item.items():

            if value == True:
                item[key] = "Yes"
            elif value == False:
                item[key] = "No"
    return api
