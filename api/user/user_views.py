from rest_framework.views import APIView

from utils.utils_views import CustomResponse


class TestApi(APIView):
    def get(self, request):
        return CustomResponse(response={'hey': 'hey'}).get_success_response()
