
from rest_framework.views import APIView
from . import qseverse_serializer
from db.achievement import Achievement
from utils.response import CustomResponse
from utils.permission import CustomizePermission, JWTUtils
from db.user import User
class QseverseAPIView(APIView):
    def get(self, request):
        # user_id = JWTUtils.fetch_user_id(request)
        #
        # if not user_id:
        #     return CustomResponse(general_message="Invalid or missing token").get_failure_response()
        #
        # user = User.objects.filter(id=user_id).first()
        #
        # if not user:
        #     return CustomResponse(general_message="User Not Exists").get_failure_response()

        achievements = Achievement.objects.all()
        achievements_serializer = qseverse_serializer.AchievementSerializer(achievements, many=True)

        return CustomResponse(response=achievements_serializer.data).get_success_response()

    # def post(self, request):
