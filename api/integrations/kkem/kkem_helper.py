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
    def wrapper(self, *args, **kwargs):

        # Assumes that the second parameter is always `request`
        # Probably need to make this cleaner
        request = args[0]

        token = request.headers.get('token')
        integration = Integration.objects.filter(token=token).first()
        if not integration:
            return CustomResponse(
                general_message="Token invalid or missing"
            ).get_failure_response()
        else:
            result = func(self, *args, **kwargs)
        return result

    return wrapper
