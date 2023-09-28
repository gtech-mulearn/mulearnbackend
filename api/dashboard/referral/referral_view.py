import uuid

from decouple import config
from rest_framework.views import APIView

from db.task import Wallet, MucoinInviteLog, MucoinActivityLog, TaskList
from db.user import UserReferralLink, User
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import RefferalType, TasksTypesHashtag
from utils.utils import DateTimeUtils
from utils.utils import send_template_mail
from .referral_serializer import ReferralListSerializer

FROM_MAIL = config('FROM_MAIL')


class Referral(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request):
        receiver_email = request.data.get("email")
        invite_type = request.data.get('invite_type')
        if (not receiver_email) or (User.objects.filter(email=receiver_email).exists()):
            return CustomResponse(
                general_message="Sorry, but it seems like this email is either invalid or already associated with an existing user.").get_failure_response()

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
                invite_log = MucoinInviteLog.objects.create(id=uuid.uuid4(), user=user, email=receiver_email,
                                                            invite_code=uuid.uuid4(),
                                                            created_by=user,
                                                            created_at=DateTimeUtils.get_current_utc_time())

                user_context = {
                    "full_name": user.fullname,
                    "email": receiver_email,
                    "mu_id": user.mu_id,
                    'invite_code': invite_log.invite_code,
                }
                send_template_mail(context=user_context, subject="AN INVITE TO Mucoin✨", address=["mucoin.html"])
                task = TaskList.objects.filter(title=TasksTypesHashtag.MUCOIN.value).first()
                MucoinActivityLog.objects.create(id=uuid.uuid4(), user=user, coin=1, task=task, status='Debit',
                                                 updated_by=user, updated_at=DateTimeUtils.get_current_utc_time(),
                                                 created_by=user, created_at=DateTimeUtils.get_current_utc_time())
                wallet = Wallet.objects.filter(user=user).first()
                wallet.coin -= 1
                wallet.save()

            else:
                return CustomResponse(general_message="You Don't have enough mucoins").get_failure_response()
        return CustomResponse(general_message="Invited successfully").get_success_response()


class ReferralListAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_referral_link = UserReferralLink.objects.filter(referral_id=user_id).all()
        serializer = ReferralListSerializer(user_referral_link, many=True)
        return CustomResponse(response=serializer.data).get_success_response()
