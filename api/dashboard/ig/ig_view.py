from rest_framework.views import APIView

from utils.utils_views import CustomResponse


from rest_framework.views import APIView
from rest_framework.response import Response
from task.models import InterestGroup , UserIgLink

from django.http import JsonResponse

ALL_FIELDS = {
    "id": "id",
    "name": "name",
    "updated_by": "updated_by",
    "updated_at": "updated_at",
    "created_by": "created_by",
    "created_at": "created_at",
    "no_of_members" : ""
}

FIELD_NAMES, FIELD_VALUES = zip(*ALL_FIELDS.items())

FIELD_LENGTH = len(ALL_FIELDS)

DEFAULT_FIELDS = ["id", "name", "created_by"]

MAX_COLUMNS = 3


class InterestGroupAPI(APIView):
    def get(self, request):
        # Filter fields based on table name
        selected_columns = request.GET.get("fields", "").split(",")
        ig = InterestGroup.objects.select_related('id')
        if (len(selected_columns) != MAX_COLUMNS) and (
            any(field not in ALL_FIELDS for field in selected_columns)
        ):
            selected_columns = DEFAULT_FIELDS

        for field in selected_columns:
            try:
                selected_columns[selected_columns.index(field)] = ALL_FIELDS[field]
            except KeyError:
                pass
        igs = ig.values(*selected_columns)
        ig_dicts = [
            {
                selected_columns[i]: ig[selected_columns[i]]

                if selected_columns[i] in ig
                else None
                for i in range(MAX_COLUMNS)
            }
            for ig in igs
        ]

        for item in ig_dicts:
            item["no_of_users"] = UserIgLink.objects.filter(ig_id=item['id']).count()
    
    
        return CustomResponse(
            general_message={"columns": FIELD_NAMES, "len_columns": FIELD_LENGTH},
            response=ig_dicts,
        ).get_success_response()
        
    
    
