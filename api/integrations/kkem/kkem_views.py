import traceback
from datetime import datetime

from django.db.models import Prefetch
import requests
from rest_framework.views import APIView

from db.integrations import IntegrationAuthorization
from db.task import UserIgLink
from db.user import User
from utils.response import CustomResponse
from utils.utils import CommonUtils
from utils.utils import DateTimeUtils
from ..integrations_helper import token_required, send_kkm_mail
from .kkem_serializer import KKEMAuthorization, KKEMUserSerializer
import decouple
from django.db.models import Q


class KKEMBulkKarmaAPI(APIView):
    @token_required
    def get(self, request):
        from_datetime_str = request.GET.get("from_datetime")
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        token = auth_header.split(" ")[1]

        if from_datetime_str:
            try:
                from_datetime = datetime.strptime(
                    from_datetime_str, "%Y-%m-%dT%H:%M:%S"
                )
            except ValueError:
                return CustomResponse(
                    general_message="Invalid datetime format",
                ).get_failure_response()

            queryset = User.objects.filter(
                integration_authorization_user__integration__token=token,
                integration_authorization_user__verified=True,
                karma_activity_log_user__appraiser_approved=True,
                karma_activity_log_user__updated_at__gte=from_datetime,
            ).prefetch_related(
                Prefetch(
                    "user_ig_link_created_by",
                    queryset=UserIgLink.objects.select_related("ig"),
                )
            ).distinct()
        else:
            queryset = User.objects.filter(
                integration_authorization_user__integration__token=token,
                integration_authorization_user__verified=True,
                karma_activity_log_user__appraiser_approved=True,
            ).prefetch_related(
                Prefetch(
                    "user_ig_link_created_by",
                    queryset=UserIgLink.objects.select_related("ig"),
                )
            ).distinct()

        serialized_users = KKEMUserSerializer(queryset, many=True)

        return CustomResponse(response=serialized_users.data).get_success_response()


class KKEMIndividualKarmaAPI(APIView):
    @token_required
    def get(self, request, mu_id):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        token = auth_header.split(" ")[1]
        kkem_user = IntegrationAuthorization.objects.filter(
            user__mu_id=mu_id, verified=True, integration__token=token
        ).first()
        if not kkem_user:
            return CustomResponse(
                general_message="User not found"
            ).get_failure_response()

        serializer = KKEMUserSerializer(kkem_user.user)
        return CustomResponse(response=serializer.data).get_success_response()


class KKEMAuthorizationAPI(APIView):
    def post(self, request):
        request.data["verified"] = False
        serialized_set = KKEMAuthorization(data=request.data)

        try:
            if not serialized_set.is_valid():
                return CustomResponse(
                    general_message=serialized_set.errors
                ).get_failure_response()

            kkem_link = serialized_set.save()
            if hasattr(kkem_link, "user"):
                send_kkm_mail(kkem_link.user, kkem_link)
            else:
                return CustomResponse(
                    general_message="Failed to authenticate user"
                ).get_failure_response()

            return CustomResponse(
                general_message="Authorization created successfully. Email sent."
            ).get_success_response()

        except Exception as e:
            # Remove this line in production
            # traceback_info = traceback.format_exc()
            # error_message = f"An error occurred: {traceback_info}"
            return CustomResponse(general_message=str(e)).get_failure_response()

    def patch(self, request, token):
        authorization = IntegrationAuthorization.objects.filter(id=token).first()
        if not authorization:
            return CustomResponse(
                general_message="Invalid or missing Token"
            ).get_failure_response()

        authorization.verified = True
        authorization.updated_at = DateTimeUtils.get_current_utc_time()
        authorization.save()

        return CustomResponse(
            general_message="User authenticated successfully"
        ).get_success_response()


class KKEMIntegrationLogin(APIView):
    def post(self, request):
        try:
            email_or_muid = request.data.get(
                "emailOrMuid", request.data.get("mu_id", None)
            )

            password = request.data.get("password")
            dwms_id = request.data.get("dwms_id", None)
            integration = request.data.get("integration", None)

            auth_domain = decouple.config("AUTH_DOMAIN")

            response = requests.post(
                f"{auth_domain}/api/v1/auth/user-authentication/",
                data={"emailOrMuid": email_or_muid, "password": password},
            )
            response = response.json()
            if response.get("statusCode") != 200:
                return CustomResponse(
                    message=response.get("message")
                ).get_failure_response()

            res_data = response.get("response")
            access_token = res_data.get("accessToken")
            refresh_token = res_data.get("refreshToken")

            response = {
                "accessToken": access_token,
                "refreshToken": refresh_token,
            }

            if dwms_id and integration:
                request.data["verified"] = True
                serialized_set = KKEMAuthorization(data=request.data)

                if not serialized_set.is_valid():
                    return CustomResponse(
                        general_message=serialized_set.errors
                    ).get_failure_response()

                serialized_set.save()
                response["data"] = serialized_set.data

            return CustomResponse(response=response).get_success_response()

        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

        # send_mail(
        #     "Congrats, You have been successfully registered in μlearn",
        #     f" Your Muid {user_obj.mu_id}",
        #     decouple.config("EMAIL_HOST_USER"),
        #     [user_obj.email],
        #     fail_silently=False,
        # )
