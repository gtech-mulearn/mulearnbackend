from api.dashboard.profile.serializers import UserLogSerializer
from db.task import KarmaActivityLog, TotalKarma
from db.user import User
from rest_framework.views import APIView
from utils.response import CustomResponse
from utils.permission import CustomizePermission, JWTUtils


class UserLogAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        karma_activity_log = KarmaActivityLog.objects.filter(created_by=user_id).all()

        if karma_activity_log is None:
            return CustomResponse(general_message="No karma details available for user").get_success_response()

        serializer = UserLogSerializer(karma_activity_log, many=True).data
        return CustomResponse(response=serializer).get_success_response()


class EditUserDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    def put(self, request):

        user_id = JWTUtils.fetch_user_id(request)

        first_name = request.data.get('firstName')
        last_name = request.data.get('lastName')
        email = request.data.get('email')
        mobile = request.data.get('mobile')
        dob = request.data.get('dob')

        user_object = User.objects.filter(id=user_id).first()

        user_object.first_name = first_name
        user_object.last_name = last_name
        user_object.email = email
        user_object.mobile = mobile
        user_object.dob = dob
        user_object.save()

        return CustomResponse(general_message='profile edited successfully').get_success_response()
