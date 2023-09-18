from decouple import config
from django.core.mail import send_mail
from rest_framework.views import APIView

from db.task import Wallet
from db.user import UserReferralLink, User
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import RefferalType
from utils.utils import send_template_mail
from .referral_serializer import ReferralListSerializer

FROM_MAIL = config('FROM_MAIL')


class Referral(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request):
        try:
            receiver_email = request.data.get("email")
            invite_type = request.data.get('invite_type')
            if (not receiver_email) or (User.objects.filter(email=receiver_email).exists()):
                return CustomResponse(
                    general_message="Sorry, but it seems like this email is either invalid "
                                    "or already associated with an existing user.").get_failure_response()

            user_id = JWTUtils.fetch_user_id(request)
            user = User.objects.filter(id=user_id).first()
            if RefferalType.KARMA.value == invite_type:

                user = {
                    "full_name": user.fullname,
                    "email": receiver_email,
                    "mu_id": user.mu_id,
                }

                send_template_mail(context=user, subject="AN INVITE TO INSPIRE✨", address=["user_referral.html"])
            elif RefferalType.MUCOIN.value == invite_type:
                wallet = Wallet.objects.filter(user=user_id).first()

                if wallet.coin >= 1:
                    send_mail(
                        "Invite Via Mu-coin",
                        f" Here is the message. {wallet.coin}",
                        FROM_MAIL,
                        [user.email],
                        fail_silently=False)
                    wallet.coin -= 1
                    # task = TaskList.objects.filter(title=TasksTypesHashtag.MUCOIN.value).first()
                    #
                    # UserReferralLink.objects.create(
                    #     id=uuid.uuid4(),
                    #     referral=referral_provider,
                    #     is_coin=True,
                    #     user=wallet.user,
                    #     created_by=wallet.user,
                    #     created_at=DateTimeUtils.get_current_utc_time(),
                    #     updated_by=wallet.user,
                    #     updated_at=DateTimeUtils.get_current_utc_time(),
                    # )
                    # MucoinActivityLog.objects.create(id=uuid.uuid4(), user=wallet.user, coin=1.0, status="Credit",
                    #                                  task=task, updated_by=wallet.user,
                    #                                  updated_at=DateTimeUtils.get_current_utc_time(),
                    #                                  created_by=wallet.user,
                    #                                  created_at=DateTimeUtils.get_current_utc_time())
                    # wallet.save()
                    print('Mucoin', wallet.coin)
            return CustomResponse(general_message="Invited successfully").get_success_response()
        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()


class ReferralListAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        try:
            user_id = JWTUtils.fetch_user_id(request)
            user_referral_link = UserReferralLink.objects.filter(referral_id=user_id).all()
            serializer = ReferralListSerializer(user_referral_link, many=True)
            return CustomResponse(response=serializer.data).get_success_response()
        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()
