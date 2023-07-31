import decouple
from django.core.mail import send_mail
from django.template.loader import render_to_string


class mulearn_mails:
    def send_mail_mentor(self, user_data):
        email_host_user = decouple.config("EMAIL_HOST_USER")
        email_content = render_to_string(
            "mails/mentor_verification.html", {"user": user_data}
        )

        send_mail(
            subject="Role request at μLearn!",
            message=email_content,
            from_email=email_host_user,
            recipient_list=[user_data["email"]],
            html_message=email_content,
        )
