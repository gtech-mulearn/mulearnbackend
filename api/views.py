from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status


class ArticleView(APIView):
    def get(self, request):
        print("sdf")
        return Response(data={"data": "Hello Mulearn"}, status=status.HTTP_200_OK)
