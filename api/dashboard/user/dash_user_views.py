from rest_framework.views import APIView

from utils.utils_views import CustomResponse


from rest_framework.views import APIView
from rest_framework.response import Response
from user.models import User

from django.http import JsonResponse

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


class UserAPI(APIView):
    def get(self, request):
        # Filter fields based on table name
        selected_columns = request.GET.get("fields", "").split(",")

        users = User.objects.select_related("github").prefetch_related("totalkarma")

        if (len(selected_columns) != MAX_COLUMNS) and (
            any(field not in ALL_FIELDS for field in selected_columns)
        ):
            selected_columns = DEFAULT_FIELDS
            print(selected_columns)

        for field in selected_columns:
            try:
                selected_columns[selected_columns.index(field)] = ALL_FIELDS[field]
            except KeyError:
                pass
        
        print(selected_columns)

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

        return CustomResponse(
            general_message={"columns": FIELD_NAMES, "len_columns": FIELD_LENGTH},
            response=user_dicts,
        ).get_success_response()
        
        
        
def normalize(api :list) -> list:
    for item in api:
        for key, value in item.items():
            
            if value == True:
                item[key] = "Yes"
            elif value == False:
                item[key] = "No"
            
    return api
    
