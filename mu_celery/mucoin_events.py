"""μCoin event dispatcher.

Drains event_outbox to mucoin-service (contract: INTEGRATION.md in
gtech-mulearn/mucoin-service). Scheduled via CELERY_BEAT_SCHEDULE every
minute. Delivery is at-least-once with exponential backoff; mucoin-service is
idempotent by event id, so retries and duplicates are always safe. No-ops
cleanly when MUCOIN_INGEST_URL is unconfigured.
"""
import hashlib
import hmac
import json
import logging
from datetime import timedelta

import requests
from celery import shared_task
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)

BATCH_SIZE = 200
TIMEOUT_SECONDS = 10
MAX_BACKOFF_SECONDS = 3600


@shared_task
def dispatch_mucoin_events():
    ingest_url = getattr(settings, "MUCOIN_INGEST_URL", "")
    secret = getattr(settings, "MUCOIN_WEBHOOK_SECRET", "")
    if not ingest_url or not secret:
        logger.debug("mu_events: MUCOIN_INGEST_URL/MUCOIN_WEBHOOK_SECRET unset; skipping dispatch")
        return 0

    from db.mu_events import EventOutbox

    now = timezone.now()
    due = EventOutbox.objects.filter(dispatched_at__isnull=True).filter(
        Q(next_retry_at__isnull=True) | Q(next_retry_at__lte=now)
    ).order_by("created_at")[:BATCH_SIZE]

    delivered = 0
    for event in due:
        body = json.dumps({"payload": event.payload}).encode()
        signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        try:
            response = requests.post(
                ingest_url,
                data=body,
                timeout=TIMEOUT_SECONDS,
                headers={
                    "Content-Type": "application/json",
                    "X-Mu-Event-Id": event.id,
                    "X-Mu-Event-Type": event.event_type,
                    "X-Mu-Signature": signature,
                },
            )
            # 200 processed/duplicate and 202 ignored are all terminal acks.
            if response.status_code in (200, 202):
                event.dispatched_at = timezone.now()
                event.save(update_fields=["dispatched_at"])
                delivered += 1
                continue
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")
        except Exception as exc:
            event.attempts += 1
            backoff = min(MAX_BACKOFF_SECONDS, 30 * (2 ** min(event.attempts, 7)))
            event.next_retry_at = timezone.now() + timedelta(seconds=backoff)
            event.save(update_fields=["attempts", "next_retry_at"])
            logger.warning(
                "mu_events: delivery failed for %s (%s), attempt %s, retry in %ss: %s",
                event.id, event.event_type, event.attempts, backoff, exc,
            )
    return delivered
