from rest_framework.views import APIView

from db.user import User
from utils.response import CustomResponse

from .dash_user_serializer import UserDashboardSerializer


class UserAPI(APIView):
    def get(self, request):
        
        user_serializer = User.objects.all()
        user_serializer_data = UserDashboardSerializer(user_serializer, many=True).data
        
        return CustomResponse(
            response={"user": user_serializer_data}
        ).get_success_response()
