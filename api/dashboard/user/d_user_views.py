from rest_framework.views import APIView

from utils.response import CustomResponse


class HelloWorld(APIView):

    def get(self, request):
        return CustomResponse(response={'hey': "hello"}).get_success_response()
