"""
Celery tasks for push notifications. Every send happens here, never in a web
request. See docs/push-notifications.md.

Load rules:
- Work is split into chunks of config.global.chunk_size users; each chunk is
  its own task.
- When the global send budget is used up, sender.deliver() sends nothing and
  returns retry_after; the task re-queues the same chunk with that countdown.
"""
import logging
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone as dt_timezone

from celery import shared_task
from django.db import transaction
from django.db.models import F

from api.push import audience as push_audience
from api.push import engine, sender
from api.push.config import get_config

logger = logging.getLogger(__name__)

LOG_RETENTION_DAYS = 90


def _now():
    return datetime.now(dt_timezone.utc)


def _chunk_size():
    return max(50, int(get_config()["global"]["chunk_size"]))


# ── Activity (an in-app notification that also goes out as push) ────────────

@shared_task(ignore_result=True)
def send_activity_push(notif_type, category, user_ids, title, body, route, dedupe_key, data=None, variant=None):
    size = _chunk_size()
    for i in range(0, len(user_ids), size):
        chunk = user_ids[i:i + size]
        result = sender.deliver(
            chunk, "activity", notif_type,
            sender.Message(title=title, body=body, route=route, data=data or {}, variant=variant),
            dedupe_key, category=category, defer_in_quiet_hours=True,
        )
        if result.retry_after:
            send_activity_push.apply_async(
                (notif_type, category, chunk, title, body, route, dedupe_key, data),
                kwargs={"variant": variant},
                countdown=result.retry_after,
            )
            continue
        # Quiet hours: send these users the same push when their window ends.
        by_eta = defaultdict(list)
        for uid, eta in result.deferred:
            by_eta[eta.replace(minute=0, second=0, microsecond=0)].append(uid)
        for eta, uids in by_eta.items():
            send_activity_push.apply_async(
                (notif_type, category, uids, title, body, route, dedupe_key, data),
                kwargs={"variant": variant}, eta=eta,
            )


# ── Engagement ───────────────────────────────────────────────────────────────

@shared_task(ignore_result=True)
def run_engagement():
    """Hourly. Pages through users with an active device and queues one
    chunk task each, five seconds apart, so the database sees a trickle."""
    from db.push import UserPushDevice

    config = get_config()
    if config["global"].get("kill_switch"):
        return
    size = max(50, int(config["global"]["chunk_size"]))
    now_iso = _now().isoformat()
    after, n = None, 0
    while True:
        qs = UserPushDevice.objects.filter(is_active=True)
        if after:
            qs = qs.filter(user_id__gt=after)
        chunk = list(qs.order_by("user_id").values_list("user_id", flat=True).distinct()[:size])
        if not chunk:
            break
        engagement_chunk.apply_async((chunk, now_iso), countdown=n * 5)
        after, n = chunk[-1], n + 1
        if len(chunk) < size:
            break
    logger.info("push: engagement queued %d chunks", n)


@shared_task(ignore_result=True)
def engagement_chunk(user_ids, now_iso):
    now = datetime.fromisoformat(now_iso)
    config = get_config()
    candidates, history = engine.candidates_for(user_ids, now, config)
    chosen = engine.select(candidates, history, config, now)
    if not chosen:
        return
    engine.apply_variants(
        chosen, config,
        engine.recent_variant_keys(list(chosen), now, engine.ROTATION_LOOKBACK_DAYS),
        random.Random(),
    )
    result = sender.deliver(
        list(chosen), "engagement", "ENGAGEMENT",
        per_user=lambda uid: (chosen[uid].message, chosen[uid].dedupe_key),
        now=now,
    )
    if result.retry_after:
        engagement_chunk.apply_async((user_ids, now_iso), countdown=result.retry_after)


# ── Campaigns ────────────────────────────────────────────────────────────────

@shared_task(ignore_result=True)
def dispatch_due_campaigns():
    """Every minute: start scheduled campaigns whose time has come."""
    from db.push import PushCampaign

    for cid in PushCampaign.objects.filter(
        status="scheduled", scheduled_at__lte=_now()
    ).values_list("id", flat=True):
        start_campaign(cid)


def start_campaign(campaign_id):
    """Move a campaign to `sending` exactly once and queue its first chunk."""
    from db.push import PushCampaign

    claimed = PushCampaign.objects.filter(
        id=campaign_id, status__in=["draft", "scheduled"]
    ).update(status="sending", updated_at=_now())
    if claimed:
        # Queue only once `sending` is committed: a worker that ran earlier
        # would see draft/scheduled and exit, leaving the campaign stuck.
        # Under autocommit this runs immediately.
        transaction.on_commit(lambda: send_campaign_chunk.delay(campaign_id, None))
    return bool(claimed)


@shared_task(ignore_result=True)
def send_campaign_chunk(campaign_id, after):
    from db.push import PushCampaign

    campaign = PushCampaign.objects.filter(id=campaign_id).first()
    if not campaign or campaign.status != "sending":
        return  # cancelled or gone
    size = _chunk_size()
    chunk = push_audience.next_chunk(campaign.audience, after, size)
    if chunk:
        result = sender.deliver(
            chunk, "campaign", "CAMPAIGN",
            sender.Message(title=campaign.title, body=campaign.body, route=campaign.route),
            f"CAMPAIGN:{campaign.id}",
            campaign_id=campaign.id,
            respect_quiet_hours=campaign.respect_quiet_hours,
        )
        if result.retry_after:
            send_campaign_chunk.apply_async((campaign_id, after), countdown=result.retry_after)
            return
        PushCampaign.objects.filter(id=campaign_id).update(
            sent_count=F("sent_count") + result.sent,
            failed_count=F("failed_count") + result.failed,
            skipped_count=F("skipped_count") + sum(result.skipped.values()),
        )
    if len(chunk) == size:
        send_campaign_chunk.apply_async((campaign_id, chunk[-1]), countdown=2)
    else:
        PushCampaign.objects.filter(id=campaign_id, status="sending").update(
            status="sent", sent_at=_now()
        )


# ── Housekeeping ─────────────────────────────────────────────────────────────

@shared_task(ignore_result=True)
def purge_push_logs():
    """Daily: delete delivery rows older than the retention, in batches."""
    from db.push import PushDeliveryLog

    cutoff = _now() - timedelta(days=LOG_RETENTION_DAYS)
    while True:
        ids = list(
            PushDeliveryLog.objects.filter(created_at__lt=cutoff).values_list("id", flat=True)[:5000]
        )
        if not ids:
            break
        PushDeliveryLog.objects.filter(id__in=ids).delete()
