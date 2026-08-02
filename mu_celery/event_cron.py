from celery import shared_task
from django.core.management import call_command

@shared_task
def transition_event_statuses_task():
    """
    Calls the transition_event_statuses management command to update
    event statuses from published -> ongoing and ongoing -> completed.
    """
    call_command('transition_event_statuses')