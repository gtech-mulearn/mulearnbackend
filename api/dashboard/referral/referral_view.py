import decouple
from rest_framework.views import APIView

from db.user import UserReferralLink, User
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import send_dashboard_mail
from .serializer import ReferralListSerializer


class Referral(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request):
        receiver_email = request.data.get('email')
        if User.objects.filter(email=receiver_email).exists():
            return CustomResponse(general_message="User already exist").get_failure_response()

        user_id = JWTUtils.fetch_user_id(request)
        html_address = "user_email_referral.html"
        domain = decouple.config("DOMAIN_NAME")

        user = User.objects.filter(id=user_id).first()
        user_data = {'full_name': user.fullname, 'email': receiver_email, 'muid': user.mu_id,
                     'redirect': f'{domain}/api/v1/register/{user.mu_id}/'}

        send_dashboard_mail(
            user_data=user_data,
            subject="AN INVITE TO INSPIRE✨",
            address=[html_address]
        )

        return CustomResponse(general_message='Invited successfully').get_success_response()


class ReferralListAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_referral_link = UserReferralLink.objects.filter(user_id=user_id).all()
        serializer = ReferralListSerializer(user_referral_link, many=True).data
        return CustomResponse(response=serializer).get_success_response()
