import decouple
from django.core.mail import send_mail
from django.template.loader import render_to_string


def send_dashboard_mail(user_data: dict, subject: str, address: list[str]):
    """
    The function `send_user_mail` sends an email to a user with the provided user data, subject, and
    address.

    :param user_data: A dictionary containing user data such as name, email, and any other relevant
    information
    :param subject: The subject of the email that will be sent to the user
    :param address: The `address` parameter is a list of strings that represents the path to the email
    template file. It is used to specify the location of the email template file that will be rendered
    and used as the content of the email
    """

    email_host_user = decouple.config("EMAIL_HOST_USER")
    email_content = render_to_string(
        f"mails/{'/'.join(map(str, address))}", {"user": user_data}
    )

    send_mail(
        subject=subject,
        message=email_content,
        from_email=email_host_user,
        recipient_list=[user_data["email"]],
        html_message=email_content,
    )
