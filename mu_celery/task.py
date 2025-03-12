from celery import shared_task
from utils.utils import send_template_mail


@shared_task
def send_email(context: dict, subject: str, address: list[str], attachment: str = None):
    return send_template_mail(context, subject, address, attachment)
