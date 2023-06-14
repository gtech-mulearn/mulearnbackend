from rest_framework.views import APIView

from utils.permission import CustomizePermission
from utils.response import CustomResponse


class HackathonManagementAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        return CustomResponse(general_message='api created').get_success_response()
