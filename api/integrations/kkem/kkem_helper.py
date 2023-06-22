import decouple


from db.integrations import KKEMAuthorization
from utils.permission import DateTimeUtils
from utils.response import CustomResponse

from django.db import IntegrityError
from django.db.models import Q
from django.core.mail import send_mail


class HandleAuthorization:
    @classmethod
    def handle_kkem_authorization(cls, user, dwms_id):
        try:
            kkem_link = KKEMAuthorization.objects.create(
                user=user,
                dwms_id=dwms_id,
                verified=False,
                created_at=DateTimeUtils.get_current_utc_time(),
                updated_at=DateTimeUtils.get_current_utc_time(),
            )

        except IntegrityError:
            if kkem_link := KKEMAuthorization.objects.filter(
                Q(user=user) | Q(dwms_id=dwms_id), verified=True
            ).first():
                return CustomResponse(
                    general_message="Authorization already exists and is verified."
                ).get_failure_response()

        return cls.send_kkm_mail(user, kkem_link)

    @classmethod
    def send_kkm_mail(cls, user, kkem_link):
        email_host_user = decouple.config("EMAIL_HOST_USER")
        to_email = [user.email]

        domain = decouple.config("FR_DOMAIN_NAME")
        message = f"Click here to confirm the authorization {domain}/kkem-authorization?token={kkem_link.id}"
        subject = "KKEM Authorization"

        send_mail(subject, message, email_host_user, to_email, fail_silently=False)

        return CustomResponse(
            general_message="Authorization created successfully. Email sent."
        ).get_success_response()
