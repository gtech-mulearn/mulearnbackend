from rest_framework.views import APIView
from .serializers import PortalSerializer
from utils.utils_views import CustomResponse
from datetime import datetime, timedelta
import pytz
from user.models import Students, StudentKarma
from portal.models import Portal, PortalUserAuth, PortalUserMailValidate
from decouple import config
from django.core.mail import send_mail
from django.conf import settings
from uuid import uuid4


# class AddPortal(APIView):
#     def post(self, request):
#         print(request)
#         serializer = PortalSerializer(data=request.data)
#         if serializer.is_valid():
#             obj = serializer.save()
#             return CustomResponse(response={"access_id": obj.access_id}).get_success_response()
#         else:
#             return CustomResponse(has_error=True, status_code=400, message=serializer.errors).get_failure_response()


class MuidValidate(APIView):
    def post(self, request):
        portal_key = request.headers.get('portalKey')
        portal = Portal.objects.filter(portal_key=portal_key).first()
        if portal is None:
            return CustomResponse({"hasError":True,"statusCode":400,"message":"Invalid Portal","response":{}}).get_failure_response() 
        name = request.data.get('name')
        muid = request.data.get('muid')
        user = Students.objects.get(muid=muid)  
        
        if user is None:
            return CustomResponse({"hasError":True,"statusCode":400,"message":"Invalid muid","response":{}}).get_failure_response()  
        if not name:
            return CustomResponse({"hasError":True,"statusCode":400,"message":"Invalid name","response":{}}).get_failure_response() 
        
        mail_token = uuid4()
        expiry_time = datetime.now() + timedelta(seconds=1800)
        PortalUserMailValidate.objects.create(portal=portal,user=user,token=mail_token,expiry=expiry_time)
        DOMAIN_NAME = config('DOMAIN_NAME')
        portal_name = portal.name
        recipient_list = [user.email]
        subject = "Validate mu-id"
        email_from = config('EMAIL_HOST_USER')
        mail_message = f"{user.fullname} have requested to approve muid for {portal_name}.If its you click the following link to authorize {DOMAIN_NAME}/portal/user/validate/{mail_token}"
        send_mail(subject,mail_message,email_from,recipient_list)
        return CustomResponse({"hasError":False,"statusCode":200,"message":"Success","response":{"name":user.fullname,"muid":user.muid}}).get_success_response()
    

class UserMailTokenValidation(APIView):

    def post(self, request):
        mail_validation_token = request.data['token']
        utc = pytz.timezone('Asia/Kolkata')
        today_now = datetime.now(utc)
        mail_validation = PortalUserMailValidate.objects.all().values()
        print(mail_validation,'ejj')
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


class GetKarma(APIView):
    def get(self, request):
        portal_key = request.headers.get("portalKey")
        portal = Portal.objects.filter(portal_key=portal_key).first()
        if portal is None:
            return CustomResponse({"hasError": True, "statusCode": 400, "message": "Invalid Portal", "response": {}}).get_failure_response()
        muid = request.data.get("muid")
        students = Students.objects.filter(muid=muid).first()
        authorized_user = PortalUserAuth.objects.filter(user_id=students.user_id).first()
        if authorized_user and authorized_user.is_authenticated:
            karma = StudentKarma.objects.get(user_id=students.user_id)
            return CustomResponse(response={"muid": muid, "name": students.fullname, "email": students.email, "karma": karma.score}).get_success_response()
        else:
            return CustomResponse(has_error=True, status_code=400, message="user not authorized to this portal").get_failure_response()
