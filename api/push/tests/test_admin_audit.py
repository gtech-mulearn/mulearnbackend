"""Push admin endpoints write one SystemActionLog row per change.
Run ONLY with the in-memory SQLite env."""
from unittest import mock

from django.core.cache import cache
from django.db import transaction
from django.test import override_settings

from api.notification.tests.helpers import hit
from api.push import config as push_config
from api.push import fcm
from api.push.views import (
    AdminCampaignActionAPI,
    AdminCampaignAPI,
    AdminConfigAPI,
    AdminTestAPI,
)
from db.mentor import SystemActionLog
from db.push import (
    PushCampaign,
    PushConfig,
    PushDeliveryLog,
    UserPushDevice,
    UserPushPreference,
)
from db.user import Role, User, UserRoleLink
from utils.tests.unmanaged_db import UnmanagedDbTestCase, make_user

P = "/api/v1/push/admin/"
CHUNK = "mu_celery.push_tasks.send_campaign_chunk.delay"


@override_settings(FIREBASE_CREDENTIALS='{"x": 1}', PUSH_ENABLED=True)
class PushAdminAuditTests(UnmanagedDbTestCase):
    MODELS = [
        User,
        Role,
        UserRoleLink,
        SystemActionLog,
        PushCampaign,
        PushConfig,
        PushDeliveryLog,
        UserPushDevice,
        UserPushPreference,
    ]

    def setUp(self):
        super().setUp()
        self.fellow = make_user("f1", {"Fellow": True})
        self.admin = make_user("a1", {"Admins": True})

    def rows(self, action):
        return SystemActionLog.objects.filter(action_type=action)

    def create_campaign(self):
        r = hit(
            AdminCampaignAPI, "post", P, "f1", ["Fellow"],
            {"title": "Hello", "body": "World", "audience": {"type": "all"}},
        )
        assert r.data["hasError"] is False, r.data
        return r.data["response"]["id"]

    def act(self, cid, action):
        return hit(
            AdminCampaignActionAPI, "post", P, "f1", ["Fellow"],
            campaign_id=cid, action=action,
        )

    def test_campaign_create_send_cancel_are_logged(self):
        cid = self.create_campaign()
        with mock.patch(CHUNK):
            self.assertFalse(self.act(cid, "send").data["hasError"])
        self.assertFalse(self.act(cid, "cancel").data["hasError"])
        create = self.rows("PUSH_CAMPAIGN_CREATE").get()
        self.assertEqual(create.entity_name, "push_campaign")
        self.assertEqual(create.entity_id, str(cid))
        self.assertEqual(create.new_data["title"], "Hello")
        send = self.rows("PUSH_CAMPAIGN_SEND").get()
        self.assertIn("people", send.remarks)
        self.assertEqual(self.rows("PUSH_CAMPAIGN_CANCEL").count(), 1)
        self.assertEqual(SystemActionLog.objects.count(), 3)
        for row in SystemActionLog.objects.all():
            self.assertEqual(row.new_data["_audit"]["title"], "Hello", row.action_type)

    def test_send_twice_logs_once(self):
        cid = self.create_campaign()
        with mock.patch(CHUNK):
            self.assertFalse(self.act(cid, "send").data["hasError"])
            second = self.act(cid, "send")
        self.assertTrue(second.data["hasError"])
        self.assertEqual(self.rows("PUSH_CAMPAIGN_SEND").count(), 1)

    def test_send_rolls_back_when_the_log_fails(self):
        cid = self.create_campaign()
        with mock.patch(CHUNK), mock.patch(
            "api.notification.audit.record", side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(RuntimeError):
                self.act(cid, "send")
        self.assertEqual(PushCampaign.objects.get(id=cid).status, "draft")

    def test_send_queues_the_chunk_only_after_commit(self):
        cid = self.create_campaign()
        from api.notification import audit as audit_mod

        real = audit_mod.record
        with mock.patch(CHUNK) as delay:
            def check_then_record(*a, **kw):
                delay.assert_not_called()  # still inside the open transaction
                return real(*a, **kw)

            with mock.patch("api.notification.audit.record", side_effect=check_then_record):
                self.assertFalse(self.act(cid, "send").data["hasError"])
            delay.assert_called_once_with(cid, None)

    def test_failed_log_never_queues_the_chunk(self):
        cid = self.create_campaign()
        with mock.patch(CHUNK) as delay, mock.patch(
            "api.notification.audit.record", side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(RuntimeError):
                self.act(cid, "send")
        delay.assert_not_called()

    def test_test_push_without_device_is_logged_with_outcome(self):
        with mock.patch.object(fcm, "send_multicast", return_value=[]):
            r = hit(AdminTestAPI, "post", P, "f1", ["Fellow"], {"title": "T", "body": "B"})
        self.assertTrue(r.data["hasError"])
        row = self.rows("PUSH_TEST_SEND").get()
        self.assertEqual(row.entity_name, "push_test")
        self.assertEqual(row.entity_id, "f1")
        self.assertEqual(row.new_data["title"], "T")
        self.assertEqual(row.new_data["_audit"]["title"], "T")
        self.assertEqual(row.new_data["outcome"]["sent"], 0)

    def test_test_push_when_not_configured_is_logged(self):
        with override_settings(FIREBASE_CREDENTIALS=""):
            r = hit(AdminTestAPI, "post", P, "f1", ["Fellow"], {})
        self.assertTrue(r.data["hasError"])
        row = self.rows("PUSH_TEST_SEND").get()
        self.assertEqual(row.new_data["outcome"], {"error": "not configured"})

    def test_config_patch_is_all_or_nothing(self):
        r = hit(
            AdminConfigAPI, "patch", P, "a1", ["Admins"],
            {"global": {"daily_cap": 2}, "rules": {"NOPE": {}}},
        )
        self.assertTrue(r.data["hasError"])
        self.assertEqual(PushConfig.objects.count(), 0)
        self.assertEqual(SystemActionLog.objects.count(), 0)

    def test_config_patch_that_changes_nothing_saves_and_logs_nothing(self):
        r = hit(AdminConfigAPI, "patch", P, "a1", ["Admins"], {"global": {}})
        self.assertFalse(r.data["hasError"], r.data)
        self.assertEqual(PushConfig.objects.count(), 0)
        self.assertEqual(SystemActionLog.objects.count(), 0)
        hit(AdminConfigAPI, "patch", P, "a1", ["Admins"], {"global": {"daily_cap": 2}})
        stamp = PushConfig.objects.get(key="global").updated_at
        r = hit(AdminConfigAPI, "patch", P, "a1", ["Admins"], {"global": {"daily_cap": 2}})
        self.assertFalse(r.data["hasError"], r.data)
        self.assertEqual(PushConfig.objects.get(key="global").updated_at, stamp)
        self.assertEqual(SystemActionLog.objects.count(), 1)

    def test_config_patch_logs_before_and_after(self):
        r = hit(
            AdminConfigAPI, "patch", P, "a1", ["Admins"], {"global": {"daily_cap": 2}}
        )
        self.assertFalse(r.data["hasError"], r.data)
        row = self.rows("PUSH_CONFIG_UPDATE").get()
        self.assertEqual(row.entity_name, "push_config")
        self.assertEqual(row.entity_id, "config")
        self.assertEqual(row.old_data, {"global": {}})
        self.assertEqual(row.new_data["global"], {"daily_cap": 2})
        self.assertIsNone(row.new_data["_audit"]["title"])

    def test_config_cache_is_cleared_only_after_commit(self):
        push_config.get_config()  # warm the cache with the defaults
        self.assertIsNotNone(cache.get(push_config.CACHE_KEY))
        with transaction.atomic():
            push_config.set_config("global", {"daily_cap": 2}, "a1")
            # A reader inside the open transaction window must not be able
            # to re-cache the old values; the cache stays until commit.
            self.assertIsNotNone(cache.get(push_config.CACHE_KEY))
        self.assertIsNone(cache.get(push_config.CACHE_KEY))
        self.assertEqual(push_config.get_config()["global"]["daily_cap"], 2)

    def test_config_cache_survives_a_rolled_back_change(self):
        push_config.get_config()
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                push_config.set_config("global", {"daily_cap": 2}, "a1")
                raise RuntimeError
        self.assertIsNotNone(cache.get(push_config.CACHE_KEY))
        self.assertEqual(PushConfig.objects.count(), 0)
