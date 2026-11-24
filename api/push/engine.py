"""
Engagement engine: decides which learners get a nudge this hour, and which.

run (hourly, mu_celery.push_tasks.run_engagement):
  1. Page through users with an active device (keyset pagination, chunk_size),
     queueing one chunk task each, staggered.
  2. Per chunk (engagement_chunk): each rule runs ONE set-based query for the
     whole chunk and returns candidates; select() keeps each user's single
     best candidate; apply_variants() picks each one's copy version (rotated
     so nobody gets the same line twice in a row); sender.deliver() applies
     preferences, quiet hours, caps and sends.

Load spreading: non-urgent rules only consider users whose stable nudge hour
(policy.nudge_hour) equals their local hour now, so each run touches about
1/10 of learners. Urgent rules (a meeting or event about to start) consider
everyone in the chunk but only match the few with something imminent.
"""
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from api.push import config as push_config
from api.push import policy
from api.push.sender import Message

ROUTES = {
    "MEETING_SOON": "/meetings/{id}",
    "EVENT_SOON": "/events/{id}",
    "STREAK_RESCUE": "/tasks",
    "COMEBACK": "/tasks",
}

# How far back rotation looks for the versions a person already got. Longer
# than the fatigue lookback on purpose: a weekly meeting nudge needs about a
# month to cycle through its versions, and the day-30 comeback push comes 16
# to 27 days after the earlier tiers of the same absence. Delivery log rows
# are kept 90 days, so the history is there.
ROTATION_LOOKBACK_DAYS = 35


@dataclass
class Candidate:
    rule: str
    weight: int
    urgent: bool
    message: Message
    dedupe_key: str
    # Placeholder values for this person (config.RULE_PLACEHOLDERS[rule]).
    values: dict = field(default_factory=dict)


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
    """Fill placeholders; a template that can't be filled is sent as written."""
    try:
        return template.format(**values)
    except (KeyError, IndexError, ValueError, AttributeError, TypeError):
        return template


# ── Copy versions ────────────────────────────────────────────────────────────

def pick_variant(variants: list, recent: list, rng: random.Random) -> dict:
    """A random version the person hasn't had in their last len-1 nudges of
    this rule (recent: keys, newest first), so they see every version before
    any repeats."""
    if len(variants) == 1:
        return variants[0]
    blocked = set(recent[:max(1, len(variants) - 1)])
    return rng.choice([v for v in variants if v.get("key") not in blocked] or variants)


def render_variant(rule: str, variant: dict, values: dict) -> tuple:
    """(title, body) filled with values. COMEBACK has a second body for when
    there are no new tasks. Never raises: an unfillable field is sent raw."""
    body = variant.get("body") or ""
    if rule == "COMEBACK" and not values.get("count"):
        body = variant.get("body_no_tasks") or body
    return _fmt(variant.get("title") or "", **values), _fmt(body, **values)


def recent_variant_keys(user_ids: list, now: datetime, lookback_days: int) -> dict:
    """{(user_id, rule): [version key, ...newest first]} from sent nudges, in
    one query."""
    from db.push import PushDeliveryLog

    if not user_ids:
        return {}
    out = defaultdict(list)
    for uid, variant in PushDeliveryLog.objects.filter(
        user_id__in=user_ids, source="engagement", status="sent", variant__isnull=False,
        created_at__gte=now - timedelta(days=lookback_days),
    ).order_by("user_id", "-created_at").values_list("user_id", "variant"):
        parts = variant.split(":", 1)
        if len(parts) == 2 and all(parts):
            out[(uid, parts[0])].append(parts[1])
    return dict(out)


def apply_variants(chosen: dict, config: dict, recent: dict, rng: random.Random) -> None:
    """Give each chosen candidate a rotated copy version, in place."""
    for uid, c in chosen.items():
        variants = push_config.rule_variants(c.rule, config["rules"][c.rule])
        v = pick_variant(variants, recent.get((uid, c.rule), []), rng)
        c.message.title, c.message.body = render_variant(c.rule, v, c.values)
        c.message.variant = f"{c.rule}:{v.get('key')}"


def _first_message(rule: str, cfg: dict, values: dict, route: str) -> Message:
    """The default version's text; apply_variants replaces it for the send."""
    title, body = render_variant(rule, push_config.rule_variants(rule, cfg)[0], values)
    return Message(title=title, body=body, route=route)


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
        values = {"circle": m.circle_id.title, "meeting": m.title, "time": _clock(local)}
        msg = _first_message("MEETING_SOON", cfg, values, ROUTES["MEETING_SOON"].format(id=m.id))
        out[uid].append(Candidate("MEETING_SOON", int(cfg["weight"]), True, msg, f"MEETING_SOON:{m.id}",
                                  values=values))
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
        values = {"event": title, "when": f"{day} at {_clock(local)}"}
        msg = _first_message("EVENT_SOON", cfg, values, ROUTES["EVENT_SOON"].format(id=event_id))
        out[uid].append(Candidate("EVENT_SOON", int(cfg["weight"]), True, msg, f"EVENT_SOON:{event_id}",
                                  values=values))
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
            values = {"days": n, "days_plus_one": n + 1}
            msg = _first_message("STREAK_RESCUE", cfg, values, ROUTES["STREAK_RESCUE"])
            out[uid].append(Candidate("STREAK_RESCUE", int(cfg["weight"]), False, msg,
                                      f"STREAK_RESCUE:{today.isoformat()}", values=values))
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
        values = {"count": count, "days": int((now - seen).total_seconds() // 86400)}
        msg = _first_message("COMEBACK", cfg, values, ROUTES["COMEBACK"])
        out[uid].append(Candidate("COMEBACK", int(cfg["weight"]), False, msg,
                                  f"COMEBACK:{tier}:{seen:%Y%m%d}", values=values))
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
