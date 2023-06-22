from datetime import datetime
from rest_framework.views import APIView
from db.task import KarmaActivityLog, UserIgLink

from db.user import User
from db.integrations import KKEMAuthorization
from utils.utils import DateTimeUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils
from . import kkem_serializer
from .kkem_helper import HandleAuthorization

from django.db.models import Prefetch
from django.core.exceptions import ValidationError


class KKEMBulkKarmaAPI(APIView):
    def get(self, request):
        if not (from_datetime := request.GET.get("from_datetime")):
            return CustomResponse(
                general_message="Unspecified time parameter", response={}
            ).get_failure_response()

        try:
            from_datetime = datetime.strptime(from_datetime, "%Y-%m-%dT%H:%M:%S")
            users_with_updates = KarmaActivityLog.objects.filter(
                appraiser_approved=True, updated_at__gte=from_datetime
            ).values_list("created_by", flat=True)
        except ValueError:
            return CustomResponse(
                general_message="Invalid datetime format", response={}
            ).get_failure_response()

        users = KKEMAuthorization.objects.filter(
            verified=True, user__in=users_with_updates
        ).values_list("user", flat=True)

        users = User.objects.filter(pk__in=users).prefetch_related(
            Prefetch("useriglink_set", queryset=UserIgLink.objects.select_related("ig"))
        )

        queryset = CommonUtils.get_paginated_queryset(
            users,
            request,
            ["mu_id"],
        )

        serialized_users = kkem_serializer.KKEMBulkKarmaSerializer(
            queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serialized_users.data, pagination=queryset.get("pagination")
        )


class KKEMIndividualKarmaAPI(APIView):
    def get(self, request, mu_id):
        kkem_user = (
            KKEMAuthorization.objects.filter(user__mu_id=mu_id, verified=True)
            .first()
        )
        if not kkem_user:
            return CustomResponse(
                general_message="User not found"
            ).get_failure_response()
            
        serializer = kkem_serializer.KKEMBulkKarmaSerializer(kkem_user.user)

        return CustomResponse(response=serializer.data).get_success_response()


class KKEMAuthorizationAPI(APIView):
    def post(self, request):
        mu_id = request.data.get("mu_id")
        dwms_id = request.data.get("dwms_id")

        if user := User.objects.filter(mu_id=mu_id).first():
            return HandleAuthorization.handle_kkem_authorization(user, dwms_id)
        else:
            return CustomResponse(
                general_message="User doesn't exist"
            ).get_failure_response()

    def patch(self, request, token):
        if authorization := KKEMAuthorization.objects.filter(id=token).first():
            authorization.verified = True
            authorization.updated_at = DateTimeUtils.get_current_utc_time()
            authorization.save()
            return CustomResponse(
                general_message="User authenticated successfully"
            ).get_success_response()
        else:
            return CustomResponse(
                general_message="Invalid token"
            ).get_failure_response()
