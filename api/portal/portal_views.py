from datetime import datetime, timedelta
from uuid import uuid4

import pytz
from user.models import Students, StudentKarma
from portal.models import Portal, PortalUserAuth, PortalUserMailValidate
from decouple import config
from django.core.mail import send_mail
from rest_framework.views import APIView
from utils.utils_views import CustomResponse


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
            return CustomResponse({"hasError": True, "statusCode": 400, "message": "Invalid Portal",
                                   "response": {}}).get_failure_response()
        name = request.data.get('name')
        muid = request.data.get('muid')
        user = Students.objects.filter(muid=muid).first()

        if user is None:
            return CustomResponse(has_error=True, status_code=400, message="Invalid muid").get_failure_response()
        if not name:
            return CustomResponse(has_error=True, status_code=400, message="Invalid name").get_failure_response()

        mail_token = uuid4()
        expiry_time = datetime.now() + timedelta(seconds=1800)
        PortalUserMailValidate.objects.create(id=uuid4(), portal=portal, user=user, token=mail_token,
                                              expiry=expiry_time)
        DOMAIN_NAME = config('DOMAIN_NAME')
        portal_name = portal.name
        recipient_list = [user.email]
        subject = "Validate mu-id"
        email_from = config('EMAIL_HOST_USER')
        mail_message = f"{user.fullname} have requested to approve muid for {portal_name}.If its you click the following link to authorize {DOMAIN_NAME}/portal/user/authorize/{mail_token}"
        send_mail(subject, mail_message, email_from, recipient_list)

        return CustomResponse(response={"name": user.fullname, "muid": user.muid}).get_success_response()


class UserMailTokenValidation(APIView):

    def post(self, request):
        mail_validation_token = request.data['token']
        utc = pytz.timezone('Asia/Kolkata')
        today_now = datetime.now(utc)
        mail_validation = PortalUserMailValidate.objects.filter(token=mail_validation_token).first()
        if mail_validation is None:
            return CustomResponse(has_error=True, message='invalid user token',
                                  status_code=498).get_failure_response()

        expiry_date = mail_validation.expiry
        today = today_now.strftime("%Y-%m-%d %H:%M:%S")
        expiry_date = expiry_date.strftime("%Y-%m-%d %H:%M:%S")

        if expiry_date < today:
            return CustomResponse(has_error=True, message='token is expired',
                                  status_code=498).get_failure_response()

        PortalUserAuth.objects.create(id=uuid4(), portal=mail_validation.portal, user=mail_validation.user,
                                      is_authenticated=True,
                                      created_at=today_now)
        mail_validation.delete()
        return CustomResponse().get_success_response()


class GetKarma(APIView):

    def get(self, request):
        portal_key = request.headers.get("portalKey")
        portal = Portal.objects.filter(portal_key=portal_key).first()
        if portal is None:
            return CustomResponse(has_error=True, message='Invalid Portal',
                                  status_code=400).get_failure_response()

        muid = request.data.get("muid")

        students = Students.objects.filter(muid=muid).first()
        authorized_user = PortalUserAuth.objects.filter(user_id=students.user_id).first()

        if authorized_user and authorized_user.is_authenticated:
            karma = StudentKarma.objects.get(user_id=students.user_id)
            return CustomResponse(response={"muid": muid, "name": students.fullname, "email": students.email,
                                            "karma": karma.score}).get_success_response()
        else:
            return CustomResponse(has_error=True, status_code=400,
                                  message="user not authorized to this portal").get_failure_response()
