import decouple
from django.core.mail import send_mail

from db.integrations import Integration
from utils.response import CustomResponse


def send_kkm_mail(user, kkem_link):
    email_host_user = decouple.config("EMAIL_HOST_USER")
    to_email = [user.email]

    domain = decouple.config("FR_DOMAIN_NAME")
    message = f"Click here to confirm the authorization {domain}/api/v1/integrations/kkem/authorization/{kkem_link.id}/"
    subject = "KKEM Authorization"

    send_mail(subject, message, email_host_user, to_email, fail_silently=False)

    return True


def token_required(func):
    def wrapper(self, request, *args, **kwargs):
        try:
            auth_header = request.META.get("HTTP_AUTHORIZATION")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise ValueError("Invalid Authorization header")
            token = auth_header.split(" ")[1]

            integration = Integration.objects.filter(token=token).first()
            if not integration:
                raise ValueError("Invalid Authorization header")
            else:
                result = func(self, request, *args, **kwargs)
            return result
        except ValueError as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    return wrapper
