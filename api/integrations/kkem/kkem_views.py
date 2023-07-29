from datetime import datetime

from django.db.models import Prefetch
import requests
from rest_framework.views import APIView

from db.integrations import IntegrationAuthorization
from db.task import UserIgLink
from db.user import User
from utils.response import CustomResponse
import decouple

from utils.utils import DateTimeUtils

from ..integrations_helper import get_access_token, send_kkm_mail, token_required
from .kkem_serializer import KKEMAuthorization, KKEMUserSerializer


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

            queryset = (
                User.objects.filter(
                    integration_authorization_user__integration__token=token,
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
                    integration_authorization_user__integration__token=token,
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
        serialized_set = KKEMAuthorization(
            data=request.data, context={"type": "register"}
        )

        try:
            if not serialized_set.is_valid():
                return CustomResponse(
                    general_message=serialized_set.errors
                ).get_failure_response()

            kkem_link = serialized_set.save()
            send_kkm_mail(user_data=kkem_link)

            return CustomResponse(
                general_message="Authorization created successfully. Email sent."
            ).get_success_response()

        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    def patch(self, request, token):
        try:
            authorization = IntegrationAuthorization.objects.get(id=token)

            authorization.verified = True
            authorization.updated_at = DateTimeUtils.get_current_utc_time()

            password = authorization.user.password
            mu_id = authorization.user.mu_id

            response = get_access_token(mu_id, password)

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
            jsid = request.data.get("jsid", None)
            integration = request.data.get("integration", None)

            response = get_access_token(email_or_muid, password)

            if jsid and integration:
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
            # url = "https://stagging.knowledgemission.kerala.gov.in/MuLearn/api/jobseeker-details"

            # username = decouple.config("KKEM_USERNAME")
            # password = decouple.config("KKEM_PASSWORD")

            # data = f'{{"username": "{username}", "password": "{password}", "jsid": {jsid}}}'

            # response = requests.post(
            #     url, data=data, verify=False  #! Change this to True in production
            # )
            # response_data = response.json()

            # if (
            #     "request_status" in response_data
            #     and not response_data["request_status"]
            # ):
            #     error_message = response_data.get("msg", "Unknown Error")
            #     return CustomResponse(
            #         general_message=error_message
            #     ).get_failure_response()

            # elif "response" in response_data and response_data["response"].get(
            #     "req_status", False
            # ):
            #     result_data = response_data["response"]["data"]
            result_data = {
                "dwms_id": "KM0037037",
                "registration": {
                    "email_id": "lijililly1995@gmail.com",
                    "key_skills": "java",
                    "gender": "Female",
                    "mu_id": None,
                    "job_seeker_lname": "L",
                    "dob": "1995-11-09",
                    "mobile_no": "8129560431",
                    "job_seeker_fname": "Liji",
                },
                "job_seeker_id": 37037,
            }
            
            return CustomResponse(response=result_data).get_success_response()

        # else:
        #     return CustomResponse(
        #         general_message="Unknown Response Format"
        #     ).get_failure_response()

        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()
