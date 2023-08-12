from datetime import datetime, timedelta

import decouple
import jwt
import pytz
from django.core.mail import send_mail
from rest_framework.views import APIView

from db.user import UserReferralLink
from mulearnbackend.settings import SECRET_KEY
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from mulearnbackend.settings import SECRET_KEY

from db.user import UserReferralLink, User
from .serializer import ReferralListSerializer


class Referral(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request):
        receiver_email = request.data.get('email')
        receiver_name = request.data.get('name')
        user_id = JWTUtils.fetch_user_id(request)
        domain = decouple.config("DOMAIN_NAME")
        expiration_time = datetime.now(pytz.utc) + timedelta(hours=1)

        payload = {
            "user_id": user_id,
            "user_email": decouple.config('EMAIL_HOST_USER'),
            "exp": expiration_time,
        }

        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        send_mail(
            subject='AN INVITE TO INSPIRE✨',
            message=f"{domain}/api/v1/register/{token}/",
            from_email=decouple.config('EMAIL_HOST_USER'),
            recipient_list=[receiver_email],
            fail_silently=False)

        return CustomResponse(general_message='Invited successfully').get_success_response()


class ReferralListAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_referral_link = UserReferralLink.objects.filter(user_id=user_id).all()
        serializer = ReferralListSerializer(user_referral_link, many=True).data
        return CustomResponse(response=serializer).get_success_response()
