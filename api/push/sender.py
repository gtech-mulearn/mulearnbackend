"""
The one path every push takes (activity, engagement, campaign, test).

deliver() handles ONE chunk of recipients (callers keep chunks <= chunk_size).
Per chunk it does a fixed number of queries regardless of chunk size:
preferences, active devices, recent sends, existing dedupe keys. It then
applies policy.decide(), reserves global send budget, sends identical
messages together (500 tokens per FCM call), deactivates dead tokens and
writes one push_delivery_log row per recipient.

Idempotent: a recipient that already has a `sent`/`failed` row for the same
dedupe_key is skipped, so Celery retries and double-dispatches never
double-send. Skips are logged under a non-blocking key, so a user skipped
during quiet hours can still receive the same push later.
"""
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Callable, Optional

from django.db.models import Count, F, Q

from api.push import fcm, policy, throttle
from api.push.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class Message:
    title: str
    body: str
    route: Optional[str] = None
    # Extra string data for the app (never secrets).
    data: dict = field(default_factory=dict)
    # Copy version, "<RULE_OR_TYPE>:<key>", logged for per-version open rates.
    variant: Optional[str] = None


@dataclass
class DeliveryResult:
    sent: int = 0
    failed: int = 0
    skipped: dict = field(default_factory=lambda: defaultdict(int))
    deferred: list = field(default_factory=list)  # [(user_id, eta_utc)]
    retry_after: int = 0  # >0: nothing was sent, try the chunk again later

    def as_dict(self) -> dict:
        return {
            "sent": self.sent,
            "failed": self.failed,
            "skipped": dict(self.skipped),
            "deferred": len(self.deferred),
            "retry_after": self.retry_after,
        }


def _facts_for(user_ids: list, config: dict, now: datetime) -> dict:
    from db.push import PushDeliveryLog, UserPushDevice, UserPushPreference

    g = config["global"]
    facts = {
        uid: policy.UserFacts(
            user_id=uid,
            quiet_start=int(g["default_quiet_start"]),
            quiet_end=int(g["default_quiet_end"]),
            timezone=g["default_timezone"],
        )
        for uid in user_ids
    }
    for p in UserPushPreference.objects.filter(user_id__in=user_ids):
        f = facts[p.user_id]
        f.push_enabled = p.push_enabled
        f.engagement_enabled = p.engagement_enabled
        f.muted_categories = p.muted_categories or []
        f.quiet_start, f.quiet_end, f.timezone = p.quiet_start, p.quiet_end, p.timezone
    for row in (
        UserPushDevice.objects.filter(user_id__in=user_ids, is_active=True)
        .values("user_id").annotate(n=Count("id"))
    ):
        facts[row["user_id"]].active_devices = row["n"]
    # "Today" is a rolling 24 hours: one query for every recipient, whatever
    # their time zone.
    since = now - timedelta(hours=24)
    for row in (
        PushDeliveryLog.objects.filter(
            user_id__in=user_ids, status="sent", created_at__gte=since
        )
        .values("user_id")
        .annotate(
            n=Count("id"),
            eng=Count("id", filter=Q(source="engagement")),
        )
    ):
        f = facts[row["user_id"]]
        f.sent_today, f.engagement_sent_today = row["n"], row["eng"]
    return facts


def deliver(
    user_ids: list,
    source: str,
    kind: str,
    message: Optional[Message] = None,
    dedupe_key: Optional[str] = None,
    *,
    per_user: Optional[Callable[[str], Optional[tuple]]] = None,
    category: Optional[str] = None,
    campaign_id: Optional[str] = None,
    respect_quiet_hours: bool = True,
    defer_in_quiet_hours: bool = False,
    now: Optional[datetime] = None,
) -> DeliveryResult:
    """Send to one chunk of users.

    Either pass one `message` + `dedupe_key` for everyone, or `per_user`
    returning (Message, dedupe_key) per user id (engagement copy is
    personal); per_user may return None to drop a user.
    """
    from db.push import PushDeliveryLog, UserPushDevice

    result = DeliveryResult()
    user_ids = list(dict.fromkeys(u for u in user_ids if u))
    if not user_ids:
        return result
    if not fcm.is_configured():
        result.skipped["skipped_disabled"] += len(user_ids)
        return result

    now = now or datetime.now(dt_timezone.utc)
    config = get_config()

    plans = {}
    for uid in user_ids:
        plan = per_user(uid) if per_user else (message, dedupe_key)
        if plan and plan[0] and plan[1]:
            plans[uid] = plan
    if not plans:
        return result

    # Already delivered (or failed) under the same key: never again.
    keys = {plan[1] for plan in plans.values()}
    done = set(
        PushDeliveryLog.objects.filter(
            user_id__in=list(plans), dedupe_key__in=list(keys),
            status__in=["sent", "failed"],
        ).values_list("user_id", "dedupe_key")
    )
    plans = {u: p for u, p in plans.items() if (u, p[1]) not in done}
    if not plans:
        return result

    facts = _facts_for(list(plans), config, now)
    to_send, skip_rows = {}, []
    for uid, (msg, key) in plans.items():
        decision = policy.decide(
            facts[uid], source, config, now,
            category=category,
            respect_quiet_hours=respect_quiet_hours,
            defer_in_quiet_hours=defer_in_quiet_hours,
        )
        if decision.send:
            to_send[uid] = (msg, key)
        elif decision.status == "deferred":
            result.deferred.append((uid, decision.defer_until))
        else:
            result.skipped[decision.status] += 1
            skip_rows.append(_log_row(uid, source, kind, campaign_id,
                                      f"{key}~{decision.status}:{now:%Y%m%d%H}",
                                      decision.status, msg, 0, variant=msg.variant))

    if skip_rows:
        PushDeliveryLog.objects.bulk_create(skip_rows, ignore_conflicts=True, batch_size=1000)
    if not to_send:
        return result

    tokens_by_user = defaultdict(list)
    for uid, token in UserPushDevice.objects.filter(
        user_id__in=list(to_send), is_active=True
    ).values_list("user_id", "token"):
        tokens_by_user[uid].append(token)

    token_total = sum(len(t) for t in tokens_by_user.values())
    wait = throttle.reserve(token_total, int(config["global"]["max_per_minute"]))
    if wait:
        result.retry_after = wait
        return result

    # Group users whose message is identical so one FCM call covers them all.
    # The version is part of the key so each row logs the one its user got.
    groups = defaultdict(list)
    for uid, (msg, key) in to_send.items():
        groups[(msg.title, msg.body, msg.route or "", key, tuple(sorted(msg.data.items())),
                msg.variant)].append(uid)

    rows, ok_users, dead_tokens, soft_fail_tokens = [], set(), [], []
    for (title, body, route, key, data_items, variant), uids in groups.items():
        title = policy.truncate(title, 100)
        body = policy.truncate(body, 240)
        data = {"route": route, "kind": kind, "source": source, "dedupe_key": key, **dict(data_items)}
        user_of = {t: u for u in uids for t in tokens_by_user.get(u, [])}
        tokens = list(user_of)
        for i in range(0, len(tokens), fcm.MAX_TOKENS_PER_CALL):
            batch = tokens[i:i + fcm.MAX_TOKENS_PER_CALL]
            try:
                outcomes = fcm.send_multicast(batch, title, body, data)
            except Exception:
                logger.exception("push: FCM call failed kind=%s tokens=%d", kind, len(batch))
                outcomes = [fcm.TokenResult(t, False, "CALL_FAILED") for t in batch]
            for o in outcomes:
                if o.ok:
                    ok_users.add(user_of[o.token])
                elif o.dead:
                    dead_tokens.append(o.token)
                else:
                    soft_fail_tokens.append(o.token)
        for uid in uids:
            status = "sent" if uid in ok_users else "failed"
            rows.append(_log_row(uid, source, kind, campaign_id,
                                 key, status, policy_msg(title, body, route),
                                 len(tokens_by_user.get(uid, [])), variant=variant))
            if status == "sent":
                result.sent += 1
            else:
                result.failed += 1

    PushDeliveryLog.objects.bulk_create(rows, ignore_conflicts=True, batch_size=1000)
    if dead_tokens:
        UserPushDevice.objects.filter(token__in=dead_tokens).update(is_active=False)
    if soft_fail_tokens:
        UserPushDevice.objects.filter(token__in=soft_fail_tokens).update(
            failure_count=F("failure_count") + 1
        )
        # A token that keeps failing for other reasons is retired too.
        UserPushDevice.objects.filter(token__in=soft_fail_tokens, failure_count__gte=10).update(
            is_active=False
        )
    return result


def policy_msg(title: str, body: str, route: str) -> Message:
    return Message(title=title, body=body, route=route or None)


def _log_row(user_id, source, kind, campaign_id, dedupe_key, status, msg, device_count, variant=None):
    from db.push import PushDeliveryLog

    return PushDeliveryLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        source=source,
        kind=kind[:50],
        variant=variant[:40] if variant else None,
        campaign_id=campaign_id,
        dedupe_key=dedupe_key[:160],
        status=status,
        title=policy.truncate(msg.title if msg else "", 100),
        body=policy.truncate(msg.body if msg else "", 240),
        route=(msg.route if msg else None),
        device_count=device_count,
    )
