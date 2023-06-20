import uuid
import decouple

from rest_framework import serializers
from rest_framework.views import APIView

from db.user import User
from db.integrations import KKEMAuthorization
from utils.permission import get_current_utc_time
from utils.response import CustomResponse

from django.db import IntegrityError
from django.db.models import Q
from django.core.mail import send_mail


class KKEMAuthorizationAPI(APIView):
    def post(self, request):
        mu_id = request.data.get("mu_id")
        dwms_id = request.data.get("dwms_id")

        if user := User.objects.filter(mu_id=mu_id).first():
            return self.handle_kkem_authorization(user, dwms_id)
        else:
            return CustomResponse(
                general_message="User doesn't exist"
            ).get_failure_response()

    def handle_kkem_authorization(self, user, dwms_id):
        try:
            kkem_user = KKEMAuthorization.objects.create(
                user=user,
                dwms_id=dwms_id,
                verified=False,
                created_at=get_current_utc_time(),
            )

        except IntegrityError:
            if kkem_user := KKEMAuthorization.objects.filter(
                Q(user=user) | Q(dwms_id=dwms_id), verified=True
            ).first():
                return CustomResponse(
                    general_message="Authorization already exists and is verified."
                ).get_failure_response()

        return self.send_kkm_mail(user, kkem_user)

    def send_kkm_mail(self, user, kkem_user):
        email_host_user = decouple.config("EMAIL_HOST_USER")
        to_email = [user.email]

        domain = decouple.config("FR_DOMAIN_NAME")
        message = f"Click here to confirm the authorization {domain}/reset-password?token={kkem_user.id}"
        subject = "KKEM Authorization"

        send_mail(subject, message, email_host_user, to_email, fail_silently=False)

        return CustomResponse(
            general_message="Authorization created successfully. Email sent."
        ).get_success_response()
