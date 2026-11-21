"""Nudge versions: their shape, legacy overrides, rotation, rendering and the
`variant` column. Run ONLY with the in-memory SQLite env (see test_push_logic.py)."""
import random
from datetime import datetime, timedelta, timezone as tz
from types import SimpleNamespace
from unittest import mock

from django.test import override_settings

from api.notification.tests.helpers import hit
from api.push import config as cfg
from api.push import engine, fcm, sender
from api.push.sender import Message
from api.push.tests.test_push_logic import conf
from api.push.views import AdminConfigAPI
from db.mentor import SystemActionLog
from db.push import PushConfig, PushDeliveryLog, UserPushDevice, UserPushPreference
from db.user import Role, User, UserRoleLink
from utils.tests.unmanaged_db import UnmanagedDbTestCase, make_user

UTC = tz.utc
NOW = datetime(2026, 11, 17, 6, 30, tzinfo=UTC)  # 12:00 IST
STREAK = "STREAK_RESCUE"


def streak_versions():
    return cfg.DEFAULT_RULES[STREAK]["variants"]


def version(key="x", title="t", body="b", **extra):
    return {"key": key, "title": title, "body": body, **extra}


# ── shape ───────────────────────────────────────────────────────────────────

def test_default_copy_is_valid():
    for key, rule in cfg.DEFAULT_RULES.items():
        assert cfg.validate_variants(key, rule["variants"]) is None, key


def test_default_rules_carry_versions_instead_of_single_copy():
    for key, rule in cfg.DEFAULT_RULES.items():
        assert len(rule["variants"]) == 5, key
        assert not set(cfg.LEGACY_COPY_KEYS) & set(rule), key


def test_validate_variants_rejects_unknown_placeholder():
    assert "count" in cfg.validate_variants(STREAK, [{"key": "x", "title": "{count}", "body": "b"}])


def test_validate_variants_rejects_bad_keys_lengths_and_counts():
    bad = {
        "bad key": [version(key="Bad Key")],
        "long key": [version(key="k" * 17)],
        "key with newline": [version(key="keep\n")],
        "key not text": [version(key=5)],
        "long title": [version(title="x" * 41)],
        "long body": [version(body="x" * 101)],
        "blank title": [version(title="  ")],
        "body missing": [{"key": "x", "title": "t"}],
        "eleven versions": [version(key=f"v{i}") for i in range(11)],
        "no versions": [],
        "duplicate keys": [version(key="a"), version(key="a")],
        "not a list": "nope",
        "version not an object": ["nope"],
        "unknown field": [version(colour="red")],
        "voice not text": [version(voice=3)],
    }
    for label, variants in bad.items():
        assert cfg.validate_variants(STREAK, variants), label
    assert cfg.validate_variants(STREAK, [version(key=f"v{i}") for i in range(10)]) is None
    assert cfg.validate_variants(STREAK, [version(key="k" * 16, title="x" * 40, body="y" * 100)]) is None
    assert cfg.validate_variants(STREAK, [version(voice="playful")]) is None


def test_validate_variants_placeholder_rules():
    assert cfg.validate_variants(STREAK, [version(title="{days} to {days_plus_one}")]) is None
    assert cfg.validate_variants(STREAK, [version(title="{{literal}} braces")]) is None
    for title in ("{days", "days}", "{}", "{0}", "{days.real}", "{days!r}", "{days:>3}"):
        assert cfg.validate_variants(STREAK, [version(title=title)]), title
    # body_no_tasks belongs to COMEBACK only, and may only use {days}.
    assert cfg.validate_variants(STREAK, [version(body_no_tasks="x")])
    assert cfg.validate_variants(STREAK, [version(body_no_tasks=None)]) is None
    assert cfg.validate_variants("COMEBACK", [version(body="{count} new")])
    assert cfg.validate_variants("COMEBACK", [version(body="{count} new", body_no_tasks="{days} days")]) is None
    assert "count" in cfg.validate_variants("COMEBACK", [version(body="{count}", body_no_tasks="{count} new")])
    assert "MEETING_SOON" in cfg.validate_variants("MEETING_SOON", [version(title="{event}")])


# ── legacy overrides (Review Focus 4) ──────────────────────────────────────

def test_legacy_override_with_title_only_keeps_default_body():
    c = cfg.build_config({"rule:STREAK_RESCUE": {"title": "Mine {days}"}})
    v = cfg.rule_variants("STREAK_RESCUE", c["rules"]["STREAK_RESCUE"])
    assert v == [{"key": "legacy", "title": "Mine {days}", "body": "One task today keeps it going.", "body_no_tasks": None}]


def test_legacy_comeback_maps_old_keys_onto_version_fields():
    c = cfg.build_config({"rule:COMEBACK": {"body_default": "Come back soon."}})
    assert cfg.rule_variants("COMEBACK", c["rules"]["COMEBACK"]) == [{
        "key": "legacy",
        "title": "Your interest groups kept going",
        "body": "{count} new tasks since you left. Pick one up.",
        "body_no_tasks": "Come back soon.",
    }]
    c = cfg.build_config({"rule:COMEBACK": {"body_with_tasks": "{count} waiting."}})
    v = cfg.rule_variants("COMEBACK", c["rules"]["COMEBACK"])[0]
    assert (v["body"], v["body_no_tasks"]) == (
        "{count} waiting.", "It's been {days} days. Your next task is waiting.")


def test_blank_legacy_text_falls_back_to_the_default():
    c = cfg.build_config({"rule:STREAK_RESCUE": {"title": "Mine {days}", "body": "  "}})
    assert cfg.rule_variants(STREAK, c["rules"][STREAK])[0]["body"] == "One task today keeps it going."


def test_rule_variants_without_legacy_keys_returns_the_versions():
    assert cfg.rule_variants(STREAK, conf()["rules"][STREAK]) == streak_versions()
    stored = [version(key="mine", title="{days} days")]
    c = cfg.build_config({"rule:STREAK_RESCUE": {"variants": stored}})
    assert cfg.rule_variants(STREAK, c["rules"][STREAK]) == stored


# ── rotation ────────────────────────────────────────────────────────────────

def test_pick_variant_skips_the_last_n_minus_one():
    vs = [{"key": k} for k in "abc"]
    for seed in range(20):
        assert engine.pick_variant(vs, ["a", "b"], random.Random(seed))["key"] == "c"


def test_pick_variant_ignores_history_older_than_the_window():
    vs = [{"key": "a"}, {"key": "b"}]
    for seed in range(20):
        assert engine.pick_variant(vs, ["b", "a"], random.Random(seed))["key"] == "a"   # window 1 blocks only "b"


def test_pick_variant_with_one_version_always_returns_it():
    assert engine.pick_variant([{"key": "a"}], ["a"], random.Random(1))["key"] == "a"


def test_pick_variant_without_history_picks_any_version_deterministically():
    vs = [{"key": k} for k in "abcde"]
    assert {engine.pick_variant(vs, [], random.Random(s))["key"] for s in range(200)} == set("abcde")
    assert [engine.pick_variant(vs, [], random.Random(7)) for _ in range(3)] == [
        engine.pick_variant(vs, [], random.Random(7))] * 3


def test_a_person_sees_every_version_before_any_repeats():
    vs = [{"key": k} for k in "abcde"]
    rng, recent = random.Random(3), []
    for _ in range(4):
        cycle = []
        for _ in range(5):
            key = engine.pick_variant(vs, recent, rng)["key"]
            cycle.append(key)
            recent.insert(0, key)
        assert sorted(cycle) == list("abcde")


# ── rendering ───────────────────────────────────────────────────────────────

def test_render_variant_fills_every_placeholder():
    v = next(v for v in streak_versions() if v["key"] == "ctrl_s")
    assert engine.render_variant(STREAK, v, {"days": 3, "days_plus_one": 4}) == (
        "Ctrl + S your streak 💾", "3 days saved so far. Today's task makes it 4.")


def test_render_variant_comeback_uses_no_tasks_line_when_count_is_zero():
    v = version(title="Back", body="{count} new tasks.", body_no_tasks="It's been {days} days.")
    assert engine.render_variant("COMEBACK", v, {"count": 0, "days": 9}) == ("Back", "It's been 9 days.")
    assert engine.render_variant("COMEBACK", v, {"count": 4, "days": 9}) == ("Back", "4 new tasks.")


def test_render_variant_with_unknown_placeholder_falls_back_to_raw():          # Review Focus 5
    assert engine.render_variant("STREAK_RESCUE", {"key": "x", "title": "{count} t", "body": "b"}, {"days": 3})[0] == "{count} t"


def test_render_variant_never_raises_on_a_broken_stored_template():
    for template in ("{days", "{days.nope}", "{days[0]}", "{days:zz}", "{0}", "{days!x}"):
        got = engine.render_variant(STREAK, version(title=template, body="{days} ok"), {"days": 3})
        assert got == (template, "3 ok"), template


# ── apply ───────────────────────────────────────────────────────────────────

def streak_candidate(days=3):
    return engine.Candidate(
        STREAK, 70, False, Message("initial", "initial", route="/tasks"), "STREAK_RESCUE:2026-11-17",
        values={"days": days, "days_plus_one": days + 1},
    )


def test_apply_variants_sets_message_and_variant():
    c = streak_candidate(3)
    engine.apply_variants({"u1": c}, conf(), {}, random.Random(0))
    rule, key = c.message.variant.split(":")
    v = next(v for v in streak_versions() if v["key"] == key)
    assert rule == STREAK
    assert c.message.title == v["title"].format(days=3, days_plus_one=4)
    assert c.message.body == v["body"].format(days=3, days_plus_one=4)
    assert "{" not in c.message.title + c.message.body


def test_apply_variants_skips_what_the_person_saw_recently():
    c = streak_candidate()
    recent = {("u1", STREAK): ["keep", "ctrl_s", "not_found", "commit"], ("u2", STREAK): ["strong"]}
    engine.apply_variants({"u1": c}, conf(), recent, random.Random(0))
    assert c.message.variant == "STREAK_RESCUE:strong"


def test_apply_variants_uses_a_legacy_override():
    c = streak_candidate(5)
    config = cfg.build_config({"rule:STREAK_RESCUE": {"title": "Mine {days}"}})
    engine.apply_variants({"u1": c}, config, {}, random.Random(0))
    assert (c.message.title, c.message.body, c.message.variant) == (
        "Mine 5", "One task today keeps it going.", "STREAK_RESCUE:legacy")


# ── rules hand every placeholder value to the rotation ─────────────────────

def _only(out):
    (cands,) = out.values()
    (c,) = cands
    return c


def test_meeting_soon_values():
    meeting = SimpleNamespace(
        id="m1", circle_id_id="c1", circle_id=SimpleNamespace(title="Python Circle"),
        title="Week 3", meet_time=NOW + timedelta(minutes=90),
    )
    with mock.patch("db.learning_circle.CircleMeetingLog.objects") as meetings, \
            mock.patch("db.learning_circle.UserCircleLink.objects") as links:
        meetings.filter.return_value.select_related.return_value = [meeting]
        links.filter.return_value.values_list.return_value = [("u1", "c1")]
        c = _only(engine._meeting_soon(["u1"], NOW, conf()["rules"]["MEETING_SOON"], {"u1": "Asia/Kolkata"}))
    assert c.values == {"circle": "Python Circle", "meeting": "Week 3", "time": "1:30 PM"}
    assert set(c.values) == cfg.RULE_PLACEHOLDERS["MEETING_SOON"]
    assert (c.message.title, c.message.body) == ("Python Circle meets soon", "Week 3 starts at 1:30 PM. See you there.")


def test_event_soon_values():
    with mock.patch("db.events.EventInterest.objects") as interest:
        interest.filter.return_value.values_list.return_value = [("u1", "e1", "Figma Jam", NOW + timedelta(hours=3))]
        c = _only(engine._event_soon(["u1"], NOW, conf()["rules"]["EVENT_SOON"], {"u1": "Asia/Kolkata"}))
    assert c.values == {"event": "Figma Jam", "when": "today at 3:00 PM"}
    assert set(c.values) == cfg.RULE_PLACEHOLDERS["EVENT_SOON"]
    assert c.message.title == "Figma Jam is coming up"


def test_streak_rescue_values():
    evening = datetime(2026, 11, 17, 13, 0, tzinfo=UTC)  # 18:30 IST
    rows = [("u1", evening - timedelta(days=1)), ("u1", evening - timedelta(days=2))]
    with mock.patch("db.task.KarmaActivityLog.objects") as karma:
        karma.filter.return_value.values_list.return_value = rows
        c = _only(engine._streak_rescue(["u1"], evening, conf()["rules"][STREAK], {"u1": "Asia/Kolkata"}))
    assert c.values == {"days": 2, "days_plus_one": 3}
    assert set(c.values) == cfg.RULE_PLACEHOLDERS[STREAK]
    assert c.message.title == "Keep your 2-day streak"


def test_comeback_values():
    seen = NOW - timedelta(days=8, hours=5)
    with mock.patch("db.task.UserIgLink.objects") as igs, mock.patch("db.task.TaskList.objects") as tasks:
        igs.filter.return_value.values_list.return_value = [("u1", "ig1")]
        tasks.filter.return_value.values_list.return_value = []
        c = _only(engine._comeback(["u1"], NOW, conf()["rules"]["COMEBACK"], {}, {"u1": seen}))
    assert c.values == {"count": 0, "days": 8}
    assert set(c.values) == cfg.RULE_PLACEHOLDERS["COMEBACK"]
    assert c.message.body == "It's been 8 days. Your next task is waiting."


# ── database ────────────────────────────────────────────────────────────────

def ok_all(tokens, title, body, data):
    return [fcm.TokenResult(t, True) for t in tokens]


@override_settings(FIREBASE_CREDENTIALS='{"x": 1}', PUSH_ENABLED=True)
class RecentVariantsDb(UnmanagedDbTestCase):
    MODELS = [User, PushDeliveryLog, UserPushDevice, UserPushPreference, PushConfig]

    def setUp(self):
        super().setUp()
        for uid in ("u1", "u2", "u3"):
            User.objects.create(id=uid, muid=f"{uid}@mulearn", full_name=uid, email=f"{uid}@x.test")
        self.n = 0

    def log(self, uid, variant, hours_ago, source="engagement", status="sent"):
        self.n += 1
        row = PushDeliveryLog.objects.create(
            user_id=uid, source=source, kind="ENGAGEMENT", dedupe_key=f"K:{self.n}",
            status=status, title="t", body="b", variant=variant,
        )
        PushDeliveryLog.objects.filter(id=row.id).update(created_at=NOW - timedelta(hours=hours_ago))

    def test_recent_variant_keys_is_one_query_grouped_by_rule(self):
        self.log("u1", "STREAK_RESCUE:a", 48)
        self.log("u1", "STREAK_RESCUE:b", 2)
        self.log("u1", "COMEBACK:x", 30)
        # The day-3 comeback push, seen 27 days before the day-30 tier.
        self.log("u1", "COMEBACK:w", 24 * 27)
        self.log("u2", "STREAK_RESCUE:c", 5)
        # Not counted: another source, not sent, no version, unparseable,
        # older than the lookback, someone outside the chunk.
        self.log("u1", "STREAK_RESCUE:z", 1, source="activity")
        self.log("u1", "STREAK_RESCUE:z", 1, status="skipped_cap")
        self.log("u1", None, 1)
        self.log("u1", "garbage", 1)
        self.log("u1", "STREAK_RESCUE:", 1)
        self.log("u1", "STREAK_RESCUE:old", 24 * 36)
        self.log("u3", "STREAK_RESCUE:a", 1)
        with self.assertNumQueries(1):
            recent = engine.recent_variant_keys(
                ["u1", "u2"], NOW, engine.ROTATION_LOOKBACK_DAYS
            )
        self.assertEqual(recent, {
            ("u1", "STREAK_RESCUE"): ["b", "a"],
            ("u1", "COMEBACK"): ["x", "w"],
            ("u2", "STREAK_RESCUE"): ["c"],
        })

    def test_engagement_chunk_rotates_over_the_rotation_window(self):
        from mu_celery import push_tasks

        self.assertEqual(engine.ROTATION_LOOKBACK_DAYS, 35)
        chosen = {"u1": object()}
        config = {"global": {"fatigue_lookback_days": 14}}
        with mock.patch.object(push_tasks, "get_config", return_value=config), \
                mock.patch.object(push_tasks.engine, "candidates_for", return_value=({}, {})), \
                mock.patch.object(push_tasks.engine, "select", return_value=chosen), \
                mock.patch.object(push_tasks.engine, "apply_variants"), \
                mock.patch.object(push_tasks.engine, "recent_variant_keys", return_value={}) as recent, \
                mock.patch.object(push_tasks.sender, "deliver",
                                  return_value=SimpleNamespace(retry_after=None)):
            push_tasks.engagement_chunk(["u1"], NOW.isoformat())
        recent.assert_called_once_with(["u1"], NOW, engine.ROTATION_LOOKBACK_DAYS)

    def test_deliver_logs_variant_on_sent_and_skipped_rows(self):
        for uid in ("u1", "u2", "u3"):
            UserPushDevice.objects.create(user_id=uid, token=f"tok-{uid}", platform="android", last_seen_at=NOW)
        UserPushPreference.objects.create(user_id="u2", push_enabled=False)
        plans = {
            "u1": (Message("Same", "Text", variant="X:y"), "K:1"),
            "u2": (Message("Same", "Text", variant="X:y"), "K:1"),
            "u3": (Message("Same", "Text", variant="X:z"), "K:1"),
        }
        with mock.patch.object(fcm, "send_multicast", side_effect=ok_all) as send:
            r = sender.deliver(list(plans), "engagement", "ENGAGEMENT", per_user=plans.get, now=NOW)
        self.assertEqual((r.sent, dict(r.skipped)), (2, {"skipped_pref": 1}))
        # Same text, different versions: one call each, so each row keeps its own.
        self.assertEqual(send.call_count, 2)
        self.assertEqual(
            dict(PushDeliveryLog.objects.values_list("user_id", "variant")),
            {"u1": "X:y", "u2": "X:y", "u3": "X:z"},
        )
        self.assertEqual(PushDeliveryLog.objects.get(user_id="u2").status, "skipped_pref")


class ConfigPatchVariantsDb(UnmanagedDbTestCase):
    MODELS = [User, Role, UserRoleLink, SystemActionLog, PushConfig]

    def setUp(self):
        super().setUp()
        make_user("a1", {"Admins": True})

    def patch(self, data):
        return hit(AdminConfigAPI, "patch", "/api/v1/push/admin/config/", "a1", ["Admins"], data)

    def test_bad_versions_save_nothing_and_log_nothing(self):
        bad = [{"key": "x", "title": "{count}", "body": "b"}]
        r = self.patch({"global": {"daily_cap": 2}, "rules": {STREAK: {"variants": bad}}})
        self.assertTrue(r.data["hasError"])
        self.assertIn("count", str(r.data))
        self.assertEqual(PushConfig.objects.count(), 0)
        self.assertEqual(SystemActionLog.objects.count(), 0)

    def test_saving_versions_drops_old_copy_keys_and_a_repeat_is_a_no_op(self):
        PushConfig.objects.create(
            key="rule:STREAK_RESCUE", value={"title": "Mine {days}", "body": "Old", "cooldown_hours": 30})
        versions = [{"key": "mine", "title": "{days} days", "body": "Keep going."}]
        r = self.patch({"rules": {STREAK: {"variants": versions}}})
        self.assertFalse(r.data["hasError"], r.data)
        self.assertEqual(r.data["response"]["rules"][STREAK]["variants"], versions)
        row = PushConfig.objects.get(key="rule:STREAK_RESCUE")
        self.assertEqual(row.value, {"cooldown_hours": 30, "variants": versions})
        self.assertEqual(SystemActionLog.objects.get().old_data["rule:STREAK_RESCUE"]["title"], "Mine {days}")
        self.assertEqual(cfg.rule_variants(STREAK, cfg.get_config()["rules"][STREAK]), versions)

        r = self.patch({"rules": {STREAK: {"variants": versions}}})
        self.assertFalse(r.data["hasError"], r.data)
        self.assertEqual(PushConfig.objects.get(key="rule:STREAK_RESCUE").updated_at, row.updated_at)
        self.assertEqual(SystemActionLog.objects.count(), 1)

    def test_old_copy_keys_are_accepted_as_text_for_their_own_rule(self):
        self.assertFalse(self.patch({"rules": {STREAK: {"title": "Mine {days}"}}}).data["hasError"])
        self.assertEqual(PushConfig.objects.get(key="rule:STREAK_RESCUE").value, {"title": "Mine {days}"})
        self.assertFalse(self.patch({"rules": {"COMEBACK": {"body_default": "Come back."}}}).data["hasError"])
        self.assertTrue(self.patch({"rules": {STREAK: {"body": 5}}}).data["hasError"])
        self.assertTrue(self.patch({"rules": {STREAK: {"body_default": "x"}}}).data["hasError"])
        self.assertEqual(SystemActionLog.objects.count(), 2)
