import traceback
from datetime import datetime

from django.db.models import Prefetch
from rest_framework.views import APIView

from db.integrations import IntegrationAuthorization
from db.task import UserIgLink
from db.user import User
from utils.response import CustomResponse
from utils.utils import CommonUtils
from utils.utils import DateTimeUtils
from ..integrations_helper import token_required, send_kkm_mail
from .kkem_serializer import KKEMAuthorization, KKEMUserSerializer


class KKEMBulkKarmaAPI(APIView):
    @token_required
    def get(self, request):
        from_datetime = request.GET.get("from_datetime")
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        token = auth_header.split(" ")[1]
        if not from_datetime:
            return CustomResponse(
                general_message="Unspecified time parameter",
            ).get_failure_response()

        try:
            from_datetime = datetime.strptime(from_datetime, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return CustomResponse(
                general_message="Invalid datetime format",
            ).get_failure_response()

        queryset = User.objects.filter(
            integration_authorization_user__integration__token=token,
            integration_authorization_user__verified=True,
            karma_activity_log_created_by__appraiser_approved=True,
            karma_activity_log_created_by__updated_at__gte=from_datetime,
        ).prefetch_related(
            Prefetch(
                "user_ig_link_created_by",
                queryset=UserIgLink.objects.select_related("ig"),
            )
        )

        queryset = CommonUtils.get_paginated_queryset(queryset, request, ["mu_id"])
        serialized_users = KKEMUserSerializer(queryset.get("queryset"), many=True)

        return CustomResponse().paginated_response(
            data=serialized_users.data, pagination=queryset.get("pagination")
        )


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
        serialized_set = KKEMAuthorization(
            data=request.data, context={"request": request}
        )

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
