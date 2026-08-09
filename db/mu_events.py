import uuid

from django.db import models


class EventOutbox(models.Model):
    """Transactional outbox for μCoin domain events (see the mu_events app).

    Rows are written by signals in the same transaction as the triggering
    write, then delivered to mucoin-service by the Celery dispatcher in
    mu_celery/mucoin_events.py. Rows are never deleted — dispatched_at marks
    delivery, which keeps the outbox auditable and replayable
    (manage.py replay_events).
    """

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    event_type = models.CharField(max_length=64)
    muid = models.CharField(max_length=100)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    dispatched_at = models.DateTimeField(blank=True, null=True)
    attempts = models.IntegerField(default=0)
    next_retry_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "event_outbox"
