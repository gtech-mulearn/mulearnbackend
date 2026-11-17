"""Sender and device-API behaviour against real tables in in-memory SQLite.

The db.* models are managed=False, so the tables this module needs are
created with schema_editor in setUpClass. Run ONLY with the in-memory SQLite
environment (see test_push_logic.py); never against a shared database.
"""
from datetime import datetime, timedelta, timezone as tz
from unittest import mock

from django.conf import settings
from django.db import connection
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIRequestFactory

from api.push import fcm, sender
from db.push import (
    PushCampaign,
    PushConfig,
    PushDeliveryLog,
    UserPushDevice,
    UserPushPreference,
)
from db.user import User

UTC = tz.utc
NOON_IST = datetime(2026, 11, 17, 6, 30, tzinfo=UTC)
NIGHT_IST = datetime(2026, 11, 17, 18, 30, tzinfo=UTC)
LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
PUSH_MODELS = [UserPushDevice, UserPushPreference, PushDeliveryLog, PushCampaign, PushConfig]


def _with_dependencies(models):
    """Models plus every model they reference through forward FKs, in an
    order where each table is created after the tables it points at."""
    ordered, seen = [], set()

    def visit(model):
        if model in seen:
            return
        seen.add(model)
        for f in model._meta.fields:
            target = getattr(f, "related_model", None)
            if f.is_relation and target and target is not model:
                visit(target)
        ordered.append(model)

    for m in models:
        visit(m)
    return ordered


MODELS = _with_dependencies([User] + PUSH_MODELS)


def _clear():
    # TransactionTestCase's flush skips managed=False tables: clear them here.
    # Plain SQL: ORM delete() would follow cascades into tables not created here.
    with connection.cursor() as cursor:
        for model in reversed(MODELS):
            cursor.execute(f'DELETE FROM "{model._meta.db_table}"')

assert "sqlite" in settings.DATABASES["default"]["ENGINE"], "run with the in-memory SQLite env"


def ok_all(tokens, title, body, data):
    return [fcm.TokenResult(t, True) for t in tokens]


@override_settings(CACHES=LOCMEM, FIREBASE_CREDENTIALS='{"x": 1}', PUSH_ENABLED=True)
class SenderTests(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.schema_editor() as editor:
            for model in MODELS:
                editor.create_model(model)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as editor:
            for model in reversed(MODELS):
                editor.delete_model(model)
        super().tearDownClass()

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        _clear()
        self.user = User.objects.create(id="u1", muid="u1@mulearn", full_name="U One", email="u1@x.test")
        self.dev = UserPushDevice.objects.create(
            user=self.user, token="tok-1", platform="android", last_seen_at=NOON_IST
        )

    def deliver(self, now=NOON_IST, **kw):
        kw.setdefault("source", "activity")
        kw.setdefault("kind", "KARMA_AWARDED")
        msg = kw.pop("message", sender.Message("Karma!", "You earned 20 karma.", data={"type": "KARMA_AWARDED"}))
        return sender.deliver(["u1"], message=msg, dedupe_key=kw.pop("key", "K:1"), now=now, **kw)

    def test_sends_logs_and_never_double_sends(self):
        with mock.patch.object(fcm, "send_multicast", side_effect=ok_all) as send:
            r1 = self.deliver()
            r2 = self.deliver()
        self.assertEqual((r1.sent, r2.sent), (1, 0))
        self.assertEqual(send.call_count, 1)
        tokens, title, body, data = send.call_args.args
        self.assertEqual(tokens, ["tok-1"])
        self.assertEqual(data["dedupe_key"], "K:1")
        self.assertEqual(data["type"], "KARMA_AWARDED")
        row = PushDeliveryLog.objects.get(user_id="u1", dedupe_key="K:1")
        self.assertEqual((row.status, row.source, row.device_count), ("sent", "activity", 1))

    def test_dead_token_is_deactivated(self):
        dead = lambda tokens, *a: [fcm.TokenResult(t, False, "UNREGISTERED") for t in tokens]
        with mock.patch.object(fcm, "send_multicast", side_effect=dead):
            r = self.deliver()
        self.assertEqual(r.failed, 1)
        self.dev.refresh_from_db()
        self.assertFalse(self.dev.is_active)
        self.assertEqual(PushDeliveryLog.objects.get(dedupe_key="K:1").status, "failed")

    def test_quiet_hours_defer_activity_and_write_nothing(self):
        with mock.patch.object(fcm, "send_multicast", side_effect=ok_all) as send:
            r = self.deliver(now=NIGHT_IST, defer_in_quiet_hours=True)
        send.assert_not_called()
        self.assertEqual(len(r.deferred), 1)
        self.assertFalse(PushDeliveryLog.objects.exists())

    def test_skip_is_logged_without_blocking_a_later_send(self):
        UserPushPreference.objects.create(user=self.user, push_enabled=False)
        with mock.patch.object(fcm, "send_multicast", side_effect=ok_all) as send:
            r = self.deliver()
            self.assertEqual(dict(r.skipped), {"skipped_pref": 1})
            send.assert_not_called()
            UserPushPreference.objects.filter(user=self.user).update(push_enabled=True)
            r2 = self.deliver()
        self.assertEqual(r2.sent, 1)
        statuses = sorted(PushDeliveryLog.objects.values_list("status", flat=True))
        self.assertEqual(statuses, ["sent", "skipped_pref"])

    def test_daily_cap_counts_recent_sends(self):
        PushConfig.objects.create(key="global", value={"daily_cap": 1})
        with mock.patch.object(fcm, "send_multicast", side_effect=ok_all):
            self.assertEqual(self.deliver(key="K:1").sent, 1)
            r = self.deliver(key="K:2")
        self.assertEqual(dict(r.skipped), {"skipped_cap": 1})

    def test_kill_switch_stops_everything(self):
        PushConfig.objects.create(key="global", value={"kill_switch": True})
        with mock.patch.object(fcm, "send_multicast", side_effect=ok_all) as send:
            r = self.deliver()
        send.assert_not_called()
        self.assertEqual(dict(r.skipped), {"skipped_disabled": 1})

    def test_rate_budget_exhausted_sends_nothing_and_asks_to_retry(self):
        PushConfig.objects.create(key="global", value={"max_per_minute": 60})
        with mock.patch("api.push.throttle.reserve", return_value=30), \
                mock.patch.object(fcm, "send_multicast", side_effect=ok_all) as send:
            r = self.deliver()
        send.assert_not_called()
        self.assertEqual(r.retry_after, 30)
        self.assertFalse(PushDeliveryLog.objects.filter(status="sent").exists())

    def test_not_configured_is_a_quiet_no_op(self):
        with override_settings(FIREBASE_CREDENTIALS=""), \
                mock.patch.object(fcm, "send_multicast", side_effect=ok_all) as send:
            r = self.deliver()
        send.assert_not_called()
        self.assertEqual(dict(r.skipped), {"skipped_disabled": 1})

    def test_identical_messages_share_one_fcm_call(self):
        for i in range(2, 5):
            u = User.objects.create(id=f"u{i}", muid=f"u{i}@mulearn", full_name="U", email=f"u{i}@x.test")
            UserPushDevice.objects.create(user=u, token=f"tok-{i}", platform="android", last_seen_at=NOON_IST)
        with mock.patch.object(fcm, "send_multicast", side_effect=ok_all) as send:
            r = sender.deliver(["u1", "u2", "u3", "u4"], "campaign", "CAMPAIGN",
                               sender.Message("Hi", "All of you"), "CAMPAIGN:c1",
                               campaign_id="c1", now=NOON_IST)
        self.assertEqual(r.sent, 4)
        self.assertEqual(send.call_count, 1)
        self.assertEqual(len(send.call_args.args[0]), 4)
        self.assertEqual(PushDeliveryLog.objects.filter(campaign_id="c1").count(), 4)


@override_settings(CACHES=LOCMEM)
class DeviceApiTests(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.schema_editor() as editor:
            for model in MODELS:
                editor.create_model(model)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as editor:
            for model in reversed(MODELS):
                editor.delete_model(model)
        super().tearDownClass()

    def setUp(self):
        _clear()
        for uid in ("a", "b"):
            User.objects.create(id=uid, muid=f"{uid}@mulearn", full_name=uid, email=f"{uid}@x.test")

    def post_as(self, user_id, data, method="post"):
        from api.push.views import DeviceAPI

        factory = APIRequestFactory()
        request = getattr(factory, method)("/api/v1/push/devices/", data, format="json")
        with mock.patch("utils.permission.CustomizePermission.has_permission", return_value=True), \
                mock.patch("api.push.views.JWTUtils.fetch_user_id", return_value=user_id):
            return DeviceAPI.as_view()(request)

    def test_register_then_token_moves_to_the_last_account(self):
        r = self.post_as("a", {"token": "T", "platform": "android", "timezone": "Asia/Kolkata"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(UserPushDevice.objects.get(token="T").user_id, "a")
        self.post_as("b", {"token": "T", "platform": "android"})
        self.assertEqual(UserPushDevice.objects.count(), 1)
        self.assertEqual(UserPushDevice.objects.get(token="T").user_id, "b")

    def test_last_seen_is_written_at_most_hourly(self):
        self.post_as("a", {"token": "T", "platform": "android"})
        first = UserPushDevice.objects.get(token="T").last_seen_at
        self.post_as("a", {"token": "T", "platform": "android"})
        self.assertEqual(UserPushDevice.objects.get(token="T").last_seen_at, first)
        UserPushDevice.objects.filter(token="T").update(last_seen_at=first - timedelta(hours=2))
        self.post_as("a", {"token": "T", "platform": "android"})
        self.assertGreater(UserPushDevice.objects.get(token="T").last_seen_at, first - timedelta(hours=2))

    def test_validation_and_unregister_only_own_token(self):
        self.assertEqual(self.post_as("a", {"token": "", "platform": "android"}).status_code, 400)
        self.assertEqual(self.post_as("a", {"token": "T", "platform": "nokia"}).status_code, 400)
        self.post_as("a", {"token": "T", "platform": "android"})
        self.post_as("b", {"token": "T"}, method="delete")
        self.assertTrue(UserPushDevice.objects.get(token="T").is_active)
        self.post_as("a", {"token": "T"}, method="delete")
        self.assertFalse(UserPushDevice.objects.get(token="T").is_active)
