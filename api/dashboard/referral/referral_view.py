import decouple
from rest_framework.views import APIView

from db.user import UserReferralLink, User
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import send_template_mail
from .referral_serializer import ReferralListSerializer


class Referral(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request):
        try:
            receiver_email = request.data.get("email")
            if (not receiver_email) or (
                User.objects.filter(email=receiver_email).exists()
            ):
                return CustomResponse(
                    general_message=(
                        "Sorry, but it seems like this email "
                        "is either invalid or already associated "
                        "with an existing user."
                    )
                ).get_failure_response()

            user_id = JWTUtils.fetch_user_id(request)

            user = User.objects.get(id=user_id)

            user = {
                "full_name": user.fullname,
                "email": receiver_email,
                "mu_id": user.mu_id,
            }

            send_template_mail(
                context=user,
                subject="AN INVITE TO INSPIRE✨",
                address=["user_referral.html"],
            )
            return CustomResponse(
                general_message="Invited successfully"
            ).get_success_response()
        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()


class ReferralListAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        try:
            user_id = JWTUtils.fetch_user_id(request)
            user_referral_link = UserReferralLink.objects.filter(referral_id=user_id).all()
            serializer = ReferralListSerializer(user_referral_link, many=True)
            serializer.data
            return CustomResponse(response=serializer.data).get_success_response()
        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()
