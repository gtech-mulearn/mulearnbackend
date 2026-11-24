"""Every guarded team endpoint refuses the Review Focus 1 user: a token that
says Fellow while the only verified role link is Student. The refusal must
leave every table as it was and write no log row.

Each (view, method) pair is its own test. A verified Admin making the same
request is the control: it proves each request would have changed something
had it been let through. Run ONLY with the in-memory SQLite env."""
import uuid
from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.test import override_settings
from django.utils import timezone

from api.notification.activity_log_view import ActivityLogAPI
from api.notification.notification_view import (
    AdminBroadcastDispatchAPI,
    BroadcastNotificationCreateAPI,
    BroadcastNotificationDeleteAllAPI,
    BroadcastNotificationDeleteAPI,
    BroadcastNotificationUpdateAPI,
)
from api.notification.tests.helpers import hit
from api.push import fcm
from api.push.views import (
    AdminCampaignActionAPI,
    AdminCampaignAPI,
    AdminConfigAPI,
    AdminTestAPI,
)
from db.mentor import SystemActionLog
from db.notification import (
    BroadcastNotification,
    BroadcastNotificationRead,
    Notification,
)
from db.push import (
    PushCampaign,
    PushConfig,
    PushDeliveryLog,
    UserPushDevice,
    UserPushPreference,
)
from db.user import Role, User, UserRoleLink
from utils.tests.unmanaged_db import UnmanagedDbTestCase, make_user

PATH = "/api/v1/team/"
CHUNK = "mu_celery.push_tasks.send_campaign_chunk.delay"
MISMATCHED = ("rf1", ["Fellow", "Student"])  # Review Focus 1
ADMIN = ("a1", ["Admins"])

WATCHED = [
    BroadcastNotification,
    Notification,
    PushCampaign,
    PushConfig,
    PushDeliveryLog,
    SystemActionLog,
]


def snapshot() -> dict:
    return {m.__name__: list(m.objects.order_by("pk").values()) for m in WATCHED}


def no_kwargs(test):
    return {}


def broadcast(test):
    return {"broadcast_id": test.broadcast.id}


def campaign(action):
    return lambda test: {"campaign_id": test.campaign.id, "action": action}


# (name, view, method, body, url kwargs, writes)
CASES = [
    ("broadcast_create", BroadcastNotificationCreateAPI, "post",
     {"title": "T", "description": "D", "expires_at": "2026-12-01T00:00:00Z"}, no_kwargs, True),
    ("broadcast_update", BroadcastNotificationUpdateAPI, "patch",
     {"title": "Changed"}, broadcast, True),
    ("broadcast_delete", BroadcastNotificationDeleteAPI, "delete", None, broadcast, True),
    ("broadcast_delete_all", BroadcastNotificationDeleteAllAPI, "delete", None, no_kwargs, True),
    ("admin_dispatch", AdminBroadcastDispatchAPI, "post",
     {"title": "Hi", "description": "All"}, no_kwargs, True),
    ("campaign_create", AdminCampaignAPI, "post",
     {"title": "Hi", "body": "There", "audience": {"type": "all"}}, no_kwargs, True),
    ("campaign_send", AdminCampaignActionAPI, "post", None, campaign("send"), True),
    ("campaign_cancel", AdminCampaignActionAPI, "post", None, campaign("cancel"), True),
    ("test_push", AdminTestAPI, "post", {"title": "T", "body": "B"}, no_kwargs, True),
    ("config_patch", AdminConfigAPI, "patch", {"global": {"daily_cap": 2}}, no_kwargs, True),
    ("activity_log_get", ActivityLogAPI, "get", {}, no_kwargs, False),
]


def ok_all(tokens, title, body, data):
    return [fcm.TokenResult(t, True) for t in tokens]


@override_settings(FIREBASE_CREDENTIALS='{"x": 1}', PUSH_ENABLED=True)
class WriteRefusalTests(UnmanagedDbTestCase):
    MODELS = [
        User,
        Role,
        UserRoleLink,
        SystemActionLog,
        BroadcastNotification,
        BroadcastNotificationRead,
        Notification,
        PushCampaign,
        PushConfig,
        PushDeliveryLog,
        UserPushDevice,
        UserPushPreference,
    ]

    def setUp(self):
        super().setUp()
        admin = make_user("a1", {"Admins": True})
        make_user("rf1", {"Fellow": False, "Student": True})
        make_user("s1", {"Student": True})
        # Personal notification rows carry created_by = SYSTEM_ADMIN_ID.
        make_user(settings.SYSTEM_ADMIN_ID)
        for uid in ("a1", "rf1"):
            UserPushDevice.objects.create(
                user_id=uid, token=f"tok-{uid}", platform="android",
                last_seen_at=timezone.now(),
            )
        now = timezone.now()
        self.broadcast = BroadcastNotification.objects.create(
            id=uuid.uuid4(), title="Keep me", description="D", target_type="global",
            created_by=admin, created_at=now, expires_at=now + timedelta(days=1),
        )
        self.campaign = PushCampaign.objects.create(
            title="Keep me", body="B", audience={"type": "all"}, target_count=3,
            created_by=admin,
        )

    def call(self, who, view, method, body, url_kwargs):
        user, roles = who
        with mock.patch(CHUNK) as chunk, \
                mock.patch.object(fcm, "send_multicast", side_effect=ok_all) as send:
            r = hit(view, method, PATH, user, roles, body, **url_kwargs(self))
        return r, chunk, send

    def assert_refused(self, view, method, body, url_kwargs):
        before = snapshot()
        r, chunk, send = self.call(MISMATCHED, view, method, body, url_kwargs)
        self.assertIs(r.data["hasError"], True, r.data)
        self.assertEqual(snapshot(), before)
        self.assertEqual(SystemActionLog.objects.count(), 0)
        chunk.assert_not_called()
        send.assert_not_called()

    def assert_control_goes_through(self, view, method, body, url_kwargs, writes):
        before = snapshot()
        r, _, _ = self.call(ADMIN, view, method, body, url_kwargs)
        if writes:
            self.assertNotEqual(snapshot(), before, r.data)
            self.assertTrue(SystemActionLog.objects.exists(), r.data)
        else:
            self.assertIs(r.data["hasError"], False, r.data)


def _refusal(view, method, body, url_kwargs, writes):
    def test(self):
        self.assert_refused(view, method, body, url_kwargs)
    return test


def _control(view, method, body, url_kwargs, writes):
    def test(self):
        self.assert_control_goes_through(view, method, body, url_kwargs, writes)
    return test


for _name, *_case in CASES:
    setattr(WriteRefusalTests, f"test_mismatched_token_is_refused_{_name}", _refusal(*_case))
    setattr(WriteRefusalTests, f"test_verified_admin_control_{_name}", _control(*_case))
