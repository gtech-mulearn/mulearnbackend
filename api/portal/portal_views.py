from rest_framework.views import APIView
from .serializers import PortalSerializer
from utils.utils_views import CustomResponse
from portal.models import PortalUserMailValidate, PortalUserAuth
from datetime import datetime
import pytz


# class AddPortal(APIView):
#     def post(self, request):
#         print(request)
#         serializer = PortalSerializer(data=request.data)
#         if serializer.is_valid():
#             obj = serializer.save()
#             return CustomResponse(response={"access_id": obj.access_id}).get_success_response()
#         else:
#             return CustomResponse(has_error=True, status_code=400, message=serializer.errors).get_failure_response()

class UserMailTokenValidation(APIView):

    def post(self, request):
        mail_validation_token = request.data['token']
        utc = pytz.timezone('Asia/Kolkata')
        today_now = datetime.now(utc)
        mail_validation = PortalUserMailValidate.objects.all().values()
        for data in mail_validation:
            token = data['token']
            if mail_validation_token == token:
                token_row = PortalUserMailValidate.objects.filter(token=mail_validation_token).values()
                for row in token_row:
                    expiry_date = row['expiry']
                    portal = row['portal_id']
                    user = row['user_id']
                    today = today_now.strftime("%Y-%m-%d %H:%M:%S")
                    expiry_date = expiry_date.strftime("%Y-%m-%d %H:%M:%S")
                    if expiry_date > today:
                        portal_user_auth = PortalUserAuth(portal_id=portal, user_id=user, is_authenticated=True,
                                                          created_at=today_now)
                        portal_user_auth.save()
                        PortalUserMailValidate.objects.filter(token=mail_validation_token).delete()
                        return CustomResponse(has_error=False, status_code=200, message='user data validated successfully').get_success_response()
                    else:
                        return CustomResponse(has_error=True, message='token is expired', status_code=498).get_failure_response()
            else:
                return CustomResponse(has_error=True, message='invalid user token', status_code=498).get_failure_response()
        return CustomResponse(has_error=True, message='database is empty', status_code=204).get_failure_response()


