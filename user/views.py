from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status


class UserView(APIView):
    def get(self, request):
        print("sdf")
        return Response(data={"data": "Hello User"}, status=status.HTTP_200_OK)
