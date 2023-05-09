from rest_framework.views import APIView
from db.task import InterestGroup
from utils.response import CustomResponse
from .dash_ig_serializer import InterestGroupSerializer


class InterestGroupAPI(APIView):
    def get(self, request):
        ig_serializer = InterestGroup.objects.all()
        ig_serializer_data = InterestGroupSerializer(ig_serializer, many=True).data

        return CustomResponse(
            response={"InterestGroup": ig_serializer_data}
        ).get_success_response()