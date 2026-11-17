"""Pure push logic: no database, no network. Run:
DATABASE_ENGINE=django.db.backends.sqlite3 DATABASE_NAME=":memory:" ... \
  ./.venv/Scripts/python.exe -m pytest api/push/tests -q
"""
from datetime import datetime, timedelta, timezone as tz
from unittest import mock

import pytest

from api.push import config as cfg
from api.push import engine, fcm, policy, throttle
from api.push.sender import Message

UTC = tz.utc


def conf(**global_overrides):
    c = cfg.build_config({})
    c["global"].update(global_overrides)
    return c


# ── policy ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("hour,quiet", [(21, False), (22, True), (2, True), (7, True), (8, False), (13, False)])
def test_quiet_hours_wrap_midnight(hour, quiet):
    local = datetime(2026, 11, 17, hour, 30)
    assert policy.in_quiet_hours(local, 22, 8) is quiet


def test_quiet_hours_same_start_end_is_never():
    assert not policy.in_quiet_hours(datetime(2026, 1, 1, 3), 5, 5)


def test_quiet_ends_at_next_local_morning():
    # 23:30 IST = 18:00 UTC; quiet ends 08:00 IST next day = 02:30 UTC.
    now = datetime(2026, 11, 17, 18, 0, tzinfo=UTC)
    end = policy.quiet_ends_at(now, "Asia/Kolkata", 22, 8)
    assert end == datetime(2026, 11, 18, 2, 30, tzinfo=UTC)


def test_quiet_ends_at_is_now_outside_quiet_hours():
    now = datetime(2026, 11, 17, 6, 0, tzinfo=UTC)  # 11:30 IST
    assert policy.quiet_ends_at(now, "Asia/Kolkata", 22, 8) == now


def test_nudge_hour_is_stable_and_in_window():
    hours = [policy.nudge_hour(f"user-{i}", 10, 20) for i in range(2000)]
    assert all(10 <= h < 20 for h in hours)
    assert policy.nudge_hour("abc", 10, 20) == policy.nudge_hour("abc", 10, 20)
    # Spread: every hour of the window gets a share of users.
    counts = {h: hours.count(h) for h in range(10, 20)}
    assert min(counts.values()) > 2000 / 10 * 0.6


def test_unknown_timezone_falls_back():
    assert policy.zone("Not/AZone").key == "Asia/Kolkata"


@pytest.mark.parametrize("unopened,expected", [(0, 1), (1, 2), (2, 4), (3, 8), (10, 14)])
def test_fatigue_multiplier(unopened, expected):
    assert policy.fatigue_multiplier(unopened, 14) == expected


NOON_IST = datetime(2026, 11, 17, 6, 30, tzinfo=UTC)  # 12:00 IST
NIGHT_IST = datetime(2026, 11, 17, 18, 30, tzinfo=UTC)  # 00:00 IST


def facts(**kw):
    base = dict(user_id="u1", active_devices=1)
    base.update(kw)
    return policy.UserFacts(**base)


def test_decide_sends_by_default():
    assert policy.decide(facts(), policy.ACTIVITY, conf(), NOON_IST).send


def test_decide_kill_switch_wins():
    d = policy.decide(facts(), policy.ACTIVITY, conf(kill_switch=True), NOON_IST)
    assert d.status == "skipped_disabled"


def test_decide_user_preferences():
    assert policy.decide(facts(push_enabled=False), policy.ACTIVITY, conf(), NOON_IST).status == "skipped_pref"
    assert policy.decide(facts(engagement_enabled=False), policy.ENGAGEMENT, conf(), NOON_IST).status == "skipped_pref"
    # Nudges off still allows activity pushes.
    assert policy.decide(facts(engagement_enabled=False), policy.ACTIVITY, conf(), NOON_IST).send
    muted = facts(muted_categories=["KARMA"])
    assert policy.decide(muted, policy.ACTIVITY, conf(), NOON_IST, category="KARMA").status == "skipped_pref"
    assert policy.decide(muted, policy.ACTIVITY, conf(), NOON_IST, category="LC").send


def test_decide_no_device():
    assert policy.decide(facts(active_devices=0), policy.ACTIVITY, conf(), NOON_IST).status == "no_device"


def test_decide_quiet_hours_skip_or_defer():
    assert policy.decide(facts(), policy.ENGAGEMENT, conf(), NIGHT_IST).status == "skipped_quiet"
    d = policy.decide(facts(), policy.ACTIVITY, conf(), NIGHT_IST, defer_in_quiet_hours=True)
    assert d.status == "deferred"
    assert d.defer_until == datetime(2026, 11, 18, 2, 30, tzinfo=UTC)
    # A campaign may opt out of quiet hours.
    assert policy.decide(facts(), policy.CAMPAIGN, conf(), NIGHT_IST, respect_quiet_hours=False).send


def test_decide_caps():
    c = conf(daily_cap=3, engagement_daily_cap=1)
    assert policy.decide(facts(sent_today=3), policy.ACTIVITY, c, NOON_IST).status == "skipped_cap"
    assert policy.decide(facts(sent_today=1, engagement_sent_today=1), policy.ENGAGEMENT, c, NOON_IST).status == "skipped_cap"
    assert policy.decide(facts(sent_today=1, engagement_sent_today=1), policy.ACTIVITY, c, NOON_IST).send


def test_decide_test_push_ignores_prefs_caps_and_quiet():
    f = facts(push_enabled=False, sent_today=99)
    assert policy.decide(f, policy.TEST, conf(), NIGHT_IST).send


def test_truncate():
    assert policy.truncate("  a   b ", 10) == "a b"
    assert policy.truncate("x" * 20, 10) == "x" * 9 + "…"


# ── config ──────────────────────────────────────────────────────────────────

def test_build_config_merges_overrides_field_by_field():
    c = cfg.build_config({
        "global": {"daily_cap": 2},
        "rule:COMEBACK": {"enabled": False},
        "types": {"KARMA_AWARDED": False},
    })
    assert c["global"]["daily_cap"] == 2
    assert c["global"]["max_per_minute"] == cfg.DEFAULT_GLOBAL["max_per_minute"]
    assert c["rules"]["COMEBACK"]["enabled"] is False
    assert c["rules"]["COMEBACK"]["tiers_days"] == [3, 7, 14, 30]
    assert c["types"] == {"KARMA_AWARDED": False}


def test_push_allowed_for_type():
    c = cfg.build_config({"types": {"EVENT_PUBLISHED": True, "LC_INVITE": False}})
    eligible = ["IN_APP", "PUSH"]
    assert cfg.push_allowed_for_type(c, "LC_JOIN_APPROVED", eligible)
    assert not cfg.push_allowed_for_type(c, "LC_JOIN_APPROVED", ["IN_APP"])
    assert not cfg.push_allowed_for_type(c, "LC_INVITE", eligible)  # admin off
    assert cfg.push_allowed_for_type(c, "EVENT_PUBLISHED", eligible)  # admin on
    assert not cfg.push_allowed_for_type(cfg.build_config({}), "EVENT_PUBLISHED", eligible)


# ── engine ──────────────────────────────────────────────────────────────────

def cand(rule, weight, urgent, key):
    return engine.Candidate(rule, weight, urgent, Message(rule, "body"), key)


NOW = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)


def test_select_keeps_one_best_candidate_per_user():
    c = conf()
    chosen = engine.select(
        {"u1": [cand("COMEBACK", 50, False, "a"), cand("STREAK_RESCUE", 70, False, "b")]},
        {}, c, NOW,
    )
    assert chosen["u1"].rule == "STREAK_RESCUE"


def test_select_urgent_beats_non_urgent_and_ignores_cooldown():
    c = conf()
    history = {"u1": engine.History(last_sent_at=NOW - timedelta(hours=1), unopened_in_a_row=5)}
    chosen = engine.select(
        {"u1": [cand("COMEBACK", 50, False, "a"), cand("MEETING_SOON", 100, True, "m")]},
        history, c, NOW,
    )
    assert chosen["u1"].rule == "MEETING_SOON"


def test_select_cooldown_scales_with_fatigue():
    c = conf()
    cands = {"u1": [cand("COMEBACK", 50, False, "a")]}
    # Sent 30 h ago, opened: 24 h cooldown has passed.
    fresh = {"u1": engine.History(last_sent_at=NOW - timedelta(hours=30), unopened_in_a_row=0)}
    assert "u1" in engine.select(cands, fresh, c, NOW)
    # Sent 30 h ago, 2 unopened in a row: cooldown 96 h, still waiting.
    tired = {"u1": engine.History(last_sent_at=NOW - timedelta(hours=30), unopened_in_a_row=2)}
    assert "u1" not in engine.select(cands, tired, c, NOW)


def test_unopened_streak():
    t = NOW
    assert engine.unopened_streak([None, None, t, None]) == 2
    assert engine.unopened_streak([t, None]) == 0
    assert engine.unopened_streak([]) == 0


def test_streak_days_counts_back_from_yesterday():
    today = NOW.date()
    days = {today - timedelta(days=1), today - timedelta(days=2), today - timedelta(days=4)}
    assert engine.streak_days(days, today) == 2
    assert engine.streak_days({today}, today) == 0


@pytest.mark.parametrize("away,tier", [(1, None), (3, 3), (6.9, 3), (7, 7), (20, 14), (45, 30)])
def test_comeback_tier(away, tier):
    assert engine.comeback_tier(away, [3, 7, 14, 30]) == tier


# ── throttle ────────────────────────────────────────────────────────────────

def test_throttle_reserves_within_budget_then_waits():
    from django.core.cache.backends.locmem import LocMemCache

    local = LocMemCache("push-throttle-test", {})
    with mock.patch.object(throttle, "cache", local):
        t = 60 * 16_666_667 + 20.0  # 20 s into a minute
        assert throttle.reserve(600, 1000, now=t) == 0
        assert throttle.reserve(400, 1000, now=t) == 0
        assert throttle.reserve(1, 1000, now=t) == 40
        # Next minute has a fresh budget.
        assert throttle.reserve(500, 1000, now=t + 60) == 0


# ── fcm wrapper ─────────────────────────────────────────────────────────────

def test_fcm_configured_only_with_credentials_and_enabled():
    from django.test import override_settings

    with override_settings(FIREBASE_CREDENTIALS="", PUSH_ENABLED=True):
        assert not fcm.is_configured()
    with override_settings(FIREBASE_CREDENTIALS='{"type": "service_account"}', PUSH_ENABLED=False):
        assert not fcm.is_configured()
    with override_settings(FIREBASE_CREDENTIALS='{"type": "service_account"}', PUSH_ENABLED=True):
        assert fcm.is_configured()


def test_fcm_dead_token_classification():
    class UnregisteredError(Exception):
        code = "NOT_FOUND"

    assert fcm.TokenResult("t", False, fcm._error_code(UnregisteredError())).dead
    quota = type("QuotaExceededError", (Exception,), {"code": "RESOURCE_EXHAUSTED"})()
    assert not fcm.TokenResult("t", False, fcm._error_code(quota)).dead
    assert not fcm.TokenResult("t", True).dead


def test_fcm_rejects_more_than_500_tokens():
    with pytest.raises(ValueError):
        fcm.send_multicast(["t"] * 501, "a", "b", {})
