"""
Engagement engine: decides which learners get a nudge this hour, and which.

run (hourly, mu_celery.push_tasks.run_engagement):
  1. Page through users with an active device (keyset pagination, chunk_size),
     queueing one chunk task each, staggered.
  2. Per chunk (engagement_chunk): each rule runs ONE set-based query for the
     whole chunk and returns candidates; select() keeps each user's single
     best candidate; sender.deliver() applies preferences, quiet hours, caps
     and sends.

Load spreading: non-urgent rules only consider users whose stable nudge hour
(policy.nudge_hour) equals their local hour now, so each run touches about
1/10 of learners. Urgent rules (a meeting or event about to start) consider
everyone in the chunk but only match the few with something imminent.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from api.push import policy
from api.push.sender import Message

ROUTES = {
    "MEETING_SOON": "/meetings/{id}",
    "EVENT_SOON": "/events/{id}",
    "STREAK_RESCUE": "/tasks",
    "COMEBACK": "/tasks",
}


@dataclass
class Candidate:
    rule: str
    weight: int
    urgent: bool
    message: Message
    dedupe_key: str


@dataclass
class History:
    """A user's recent engagement pushes, newest first."""
    last_sent_at: Optional[datetime] = None
    unopened_in_a_row: int = 0


def _clock(local: datetime) -> str:
    """6:00 PM (no leading zero, portable across platforms)."""
    return local.strftime("%I:%M %p").lstrip("0")


def unopened_streak(opened_flags: list) -> int:
    """Leading run of unopened pushes, newest first: [None, None, t, None] → 2."""
    n = 0
    for opened in opened_flags:
        if opened is not None:
            break
        n += 1
    return n


def _fmt(template: str, **values) -> str:
    try:
        return template.format(**values)
    except (KeyError, IndexError, ValueError):
        return template


# ── Pure selection ───────────────────────────────────────────────────────────

def select(
    candidates: dict,
    history: dict,
    config: dict,
    now: datetime,
) -> dict:
    """{user_id: [Candidate]} → {user_id: Candidate}, at most one each.

    Urgent candidates always compete. Non-urgent ones are dropped while the
    user is inside their fatigue-scaled cooldown: base 24 h, doubled for each
    unopened engagement push in a row, capped at max_backoff_days."""
    g = config["global"]
    max_mult = max(1, int(g.get("max_backoff_days", 14)))
    chosen = {}
    for uid, cands in candidates.items():
        h = history.get(uid) or History()
        mult = policy.fatigue_multiplier(h.unopened_in_a_row, max_mult)
        best, best_score = None, -1.0
        for c in cands:
            if not c.urgent:
                rule_cfg = config["rules"].get(c.rule, {})
                base_hours = float(rule_cfg.get("cooldown_hours", 24))
                if h.last_sent_at and now - h.last_sent_at < timedelta(hours=base_hours * mult):
                    continue
                score = c.weight / mult
            else:
                score = float(c.weight) + 1000.0
            if score > best_score:
                best, best_score = c, score
        if best:
            chosen[uid] = best
    return chosen


def streak_days(active_dates: set, today) -> int:
    """Consecutive days with activity ending yesterday (0 if none)."""
    n, day = 0, today - timedelta(days=1)
    while day in active_dates:
        n += 1
        day -= timedelta(days=1)
    return n


def comeback_tier(days_away: float, tiers: list) -> Optional[int]:
    reached = [t for t in sorted(tiers) if days_away >= t]
    return reached[-1] if reached else None


# ── Rules (one query per chunk each) ─────────────────────────────────────────

def _meeting_soon(user_ids, now, cfg, tz_of):
    from db.learning_circle import CircleMeetingLog, UserCircleLink

    lo = now + timedelta(minutes=int(cfg["lead_minutes_min"]))
    hi = now + timedelta(minutes=int(cfg["lead_minutes_max"]))
    meetings = {
        m.circle_id_id: m
        for m in CircleMeetingLog.objects.filter(meet_time__gte=lo, meet_time__lt=hi)
        .select_related("circle_id")
    }
    if not meetings:
        return {}
    out = defaultdict(list)
    for uid, circle_id in UserCircleLink.objects.filter(
        user_id__in=user_ids, circle_id__in=list(meetings), accepted=True
    ).values_list("user_id", "circle_id"):
        m = meetings[circle_id]
        local = m.meet_time.astimezone(policy.zone(tz_of.get(uid)))
        msg = Message(
            title=_fmt(cfg["title"], circle=m.circle_id.title),
            body=_fmt(cfg["body"], meeting=m.title, time=_clock(local)),
            route=ROUTES["MEETING_SOON"].format(id=m.id),
        )
        out[uid].append(Candidate("MEETING_SOON", int(cfg["weight"]), True, msg, f"MEETING_SOON:{m.id}"))
    return out


def _event_soon(user_ids, now, cfg, tz_of):
    from db.events import EventInterest

    hi = now + timedelta(hours=int(cfg["lead_hours"]))
    out = defaultdict(list)
    rows = EventInterest.objects.filter(
        user_id__in=user_ids, event__start_datetime__gte=now, event__start_datetime__lt=hi
    ).values_list("user_id", "event_id", "event__title", "event__start_datetime")
    for uid, event_id, title, starts in rows:
        local = starts.astimezone(policy.zone(tz_of.get(uid)))
        day = "today" if local.date() == now.astimezone(local.tzinfo).date() else "tomorrow"
        when = f"{day} at {_clock(local)}"
        msg = Message(
            title=_fmt(cfg["title"], event=title),
            body=_fmt(cfg["body"], when=when),
            route=ROUTES["EVENT_SOON"].format(id=event_id),
        )
        out[uid].append(Candidate("EVENT_SOON", int(cfg["weight"]), True, msg, f"EVENT_SOON:{event_id}"))
    return out


def _streak_rescue(user_ids, now, cfg, tz_of):
    from db.task import KarmaActivityLog

    # Only users whose local time is in the evening window right now.
    eligible = [
        u for u in user_ids
        if int(cfg["local_hour_start"]) <= policy.local_now(now, tz_of.get(u)).hour < int(cfg["local_hour_end"])
    ]
    if not eligible:
        return {}
    since = now - timedelta(days=int(cfg["min_streak_days"]) + 8)
    days = defaultdict(set)
    for uid, created in KarmaActivityLog.objects.filter(
        user_id__in=eligible, created_at__gte=since
    ).values_list("user_id", "created_at"):
        days[uid].add(created.astimezone(policy.zone(tz_of.get(uid))).date())
    out = defaultdict(list)
    for uid in eligible:
        today = policy.local_now(now, tz_of.get(uid)).date()
        if today in days[uid]:
            continue
        n = streak_days(days[uid], today)
        if n >= int(cfg["min_streak_days"]):
            msg = Message(
                title=_fmt(cfg["title"], days=n), body=cfg["body"], route=ROUTES["STREAK_RESCUE"]
            )
            out[uid].append(Candidate("STREAK_RESCUE", int(cfg["weight"]), False, msg,
                                      f"STREAK_RESCUE:{today.isoformat()}"))
    return out


def _comeback(user_ids, now, cfg, tz_of, last_seen):
    from db.task import TaskList, UserIgLink

    tiers = [int(t) for t in cfg["tiers_days"]]
    away = {}
    for uid in user_ids:
        seen = last_seen.get(uid)
        if not seen:
            continue
        tier = comeback_tier((now - seen).total_seconds() / 86400, tiers)
        if tier:
            away[uid] = (tier, seen)
    if not away:
        return {}
    igs = defaultdict(set)
    for uid, ig in UserIgLink.objects.filter(user_id__in=list(away)).values_list("user_id", "ig_id"):
        igs[uid].add(ig)
    oldest = min(seen for _, seen in away.values())
    all_igs = set().union(*igs.values()) if igs else set()
    new_tasks = defaultdict(list)
    if all_igs:
        for ig, created in TaskList.objects.filter(
            ig_id__in=list(all_igs), active=True, created_at__gt=oldest
        ).values_list("ig_id", "created_at"):
            new_tasks[ig].append(created)
    out = defaultdict(list)
    for uid, (tier, seen) in away.items():
        count = sum(1 for ig in igs[uid] for c in new_tasks.get(ig, []) if c > seen)
        body = _fmt(cfg["body_with_tasks"], count=count) if count else cfg["body_default"]
        msg = Message(title=cfg["title"], body=body, route=ROUTES["COMEBACK"])
        out[uid].append(Candidate("COMEBACK", int(cfg["weight"]), False, msg,
                                  f"COMEBACK:{tier}:{seen:%Y%m%d}"))
    return out


# ── Chunk ────────────────────────────────────────────────────────────────────

def candidates_for(user_ids: list, now: datetime, config: dict) -> tuple:
    """Gather facts and run every enabled rule for one chunk.
    Returns (candidates, history)."""
    from django.db.models import Max

    from db.push import PushDeliveryLog, UserPushDevice, UserPushPreference

    g, rules = config["global"], config["rules"]
    tz_of, last_seen = {}, {}
    for row in (
        UserPushDevice.objects.filter(user_id__in=user_ids, is_active=True)
        .values("user_id", "timezone").annotate(seen=Max("last_seen_at"))
    ):
        tz_of.setdefault(row["user_id"], row["timezone"] or g["default_timezone"])
        prev = last_seen.get(row["user_id"])
        last_seen[row["user_id"]] = max(prev, row["seen"]) if prev else row["seen"]
    for uid, tz in UserPushPreference.objects.filter(user_id__in=user_ids).values_list("user_id", "timezone"):
        tz_of[uid] = tz or tz_of.get(uid)

    # Non-urgent rules only see users whose nudge hour is now.
    in_slot = [
        u for u in user_ids
        if policy.nudge_hour(u, int(g["nudge_window_start"]), int(g["nudge_window_end"]))
        == policy.local_now(now, tz_of.get(u)).hour
    ]

    found = defaultdict(list)

    def add(result):
        for uid, cands in result.items():
            found[uid].extend(cands)

    if rules["MEETING_SOON"].get("enabled"):
        add(_meeting_soon(user_ids, now, rules["MEETING_SOON"], tz_of))
    if rules["EVENT_SOON"].get("enabled"):
        add(_event_soon(user_ids, now, rules["EVENT_SOON"], tz_of))
    if rules["STREAK_RESCUE"].get("enabled"):
        # Streak rescue has its own evening window instead of the slot.
        add(_streak_rescue(user_ids, now, rules["STREAK_RESCUE"], tz_of))
    if rules["COMEBACK"].get("enabled") and in_slot:
        add(_comeback(in_slot, now, rules["COMEBACK"], tz_of, last_seen))

    history = {}
    if found:
        lookback = now - timedelta(days=int(g.get("fatigue_lookback_days", 14)))
        sent = defaultdict(list)
        for uid, created, opened in PushDeliveryLog.objects.filter(
            user_id__in=list(found), source="engagement", status="sent", created_at__gte=lookback
        ).order_by("user_id", "-created_at").values_list("user_id", "created_at", "opened_at"):
            sent[uid].append((created, opened))
        for uid, rows in sent.items():
            history[uid] = History(
                last_sent_at=rows[0][0],
                unopened_in_a_row=unopened_streak([o for _, o in rows]),
            )
    return found, history
