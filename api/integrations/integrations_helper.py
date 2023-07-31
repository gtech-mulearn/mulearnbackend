import decouple
import requests
from django.core.mail import send_mail
from django.template.loader import render_to_string

from db.integrations import Integration
from utils.response import CustomResponse


def send_kkm_mail(user_data):
    email_host_user = decouple.config("EMAIL_HOST_USER")
    base_url = decouple.config("FR_DOMAIN_NAME")
    email_content = render_to_string(
        "mails/KKEM/verify_integration.html", {"user": user_data, "base_url": base_url}
    )

    send_mail(
        subject="KKEM integration request!",
        message=email_content,
        from_email=email_host_user,
        recipient_list=[user_data["email"]],
        html_message=email_content,
    )


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


def get_access_token(email_or_muid, password):
    auth_domain = decouple.config("AUTH_DOMAIN")

    response = requests.post(
        f"{auth_domain}/api/v1/auth/user-authentication/",
        data={"emailOrMuid": email_or_muid, "password": password},
    )
    response = response.json()
    if response.get("statusCode") != 200:
        raise ValueError(response.get("message"))

    res_data = response.get("response")
    access_token = res_data.get("accessToken")
    refresh_token = res_data.get("refreshToken")

    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
    }
