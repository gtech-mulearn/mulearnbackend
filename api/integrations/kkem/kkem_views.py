from datetime import datetime

from django.db.models import Prefetch
import requests
from rest_framework.views import APIView

from db.integrations import IntegrationAuthorization
from db.task import UserIgLink
from db.user import User
from utils.response import CustomResponse
from utils.utils import DateTimeUtils
from utils.types import IntegrationType

from .. import integrations_helper
from .kkem_serializer import KKEMAuthorization, KKEMUserSerializer


class KKEMBulkKarmaAPI(APIView):
    @integrations_helper.token_required(IntegrationType.KKEM.value)
    def get(self, request):
        if from_datetime_str := request.GET.get("from_datetime"):
            try:
                from_datetime = datetime.strptime(
                    from_datetime_str, "%Y-%m-%dT%H:%M:%S"
                )
            except ValueError:
                return CustomResponse(
                    general_message="Invalid datetime format",
                ).get_failure_response()

            queryset = (
                User.objects.filter(
                    integration_authorization_user__integration__name=IntegrationType.KKEM.value,
                    integration_authorization_user__verified=True,
                    karma_activity_log_user__appraiser_approved=True,
                    karma_activity_log_user__updated_at__gte=from_datetime,
                )
                .prefetch_related(
                    Prefetch(
                        "user_ig_link_created_by",
                        queryset=UserIgLink.objects.select_related("ig"),
                    )
                )
                .distinct()
            )
        else:
            queryset = (
                User.objects.filter(
                    integration_authorization_user__integration__name=IntegrationType.KKEM.value,
                    integration_authorization_user__verified=True,
                    karma_activity_log_user__appraiser_approved=True,
                )
                .prefetch_related(
                    Prefetch(
                        "user_ig_link_created_by",
                        queryset=UserIgLink.objects.select_related("ig"),
                    )
                )
                .distinct()
            )

        serialized_users = KKEMUserSerializer(queryset, many=True)

        return CustomResponse(response=serialized_users.data).get_success_response()


class KKEMIndividualKarmaAPI(APIView):
    @integrations_helper.token_required(IntegrationType.KKEM.value)
    def get(self, request, mu_id):
        kkem_user = IntegrationAuthorization.objects.filter(
            user__mu_id=mu_id,
            verified=True,
            integration__name=IntegrationType.KKEM.value,
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
        serialized_set = KKEMAuthorization(
            data=request.data, context={"type": "register"}
        )

        try:
            if not serialized_set.is_valid():
                return CustomResponse(
                    general_message=serialized_set.errors
                ).get_failure_response()

            kkem_link = serialized_set.save()

            confirmation_token = integrations_helper.generate_confirmation_token(
                kkem_link["link_id"]
            )
            
            integrations_helper.send_integration_mail(
                user_data=kkem_link,
                token=confirmation_token,
                subject="KKEM integration request!",
                address=("KKEM", "verify_integration.html"),
            )

            return CustomResponse(
                general_message="Authorization created successfully. Email sent."
            ).get_success_response()

        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    def patch(self, request, token):
        try:
            link_id = integrations_helper.get_authorization_id(token)
            authorization = IntegrationAuthorization.objects.get(id=link_id)

            authorization.verified = True
            authorization.updated_at = DateTimeUtils.get_current_utc_time()

            user_id = authorization.user.id
            response = integrations_helper.get_access_token(token=user_id)

            authorization.save()
            return CustomResponse(
                general_message="User authenticated successfully", response=response
            ).get_success_response()

        except IntegrationAuthorization.DoesNotExist:
            return CustomResponse(
                general_message="Invalid or missing Token"
            ).get_failure_response()

        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()


class KKEMIntegrationLogin(APIView):
    def post(self, request):
        try:
            email_or_muid = request.data.get(
                "emailOrMuid", request.data.get("mu_id", None)
            )
            password = request.data.get("password")
            response = integrations_helper.get_access_token(email_or_muid, password)

            if request.data.get("jsid", None):
                request.data["verified"] = True
                serialized_set = KKEMAuthorization(
                    data=request.data, context={"type": "login"}
                )

                if not serialized_set.is_valid():
                    return CustomResponse(
                        general_message=serialized_set.errors
                    ).get_failure_response()

                serialized_set.save()
                response["data"] = serialized_set.data

            return CustomResponse(response=response).get_success_response()

        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()


class KKEMdetailsFetchAPI(APIView):
    def get(self, request, jsid):
        try:
            url = "https://stagging.knowledgemission.kerala.gov.in/MuLearn/api/jobseeker-details"

            data = f'{{"job_seeker_id": {jsid}}}'

            headers = {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJtdUxlYXJuIiwiaWF0IjoxNjkxMDc1NzE0LCJleHAiOjE3ODU3NzAxMTQsImNsaWVudC1pZCI6Im11TGVhcm4tZHdtcy1hcGkifQ.L6XdWWjur6GThkxJ6BCktC_vdmgGsLDy3d1UQV4kn5o"
            }

            response = requests.post(url, data=data, headers=headers)
            response_data = response.json()

            if (
                "request_status" in response_data
                and not response_data["request_status"]
            ):
                error_message = response_data.get("msg", "Unknown Error")
                return CustomResponse(
                    general_message=error_message
                ).get_failure_response()

            elif "response" in response_data and response_data["response"].get(
                "req_status", False
            ):
                result_data = response_data["response"]["data"]

            return CustomResponse(response=result_data).get_success_response()

        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()
