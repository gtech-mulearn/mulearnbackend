"""Send-to-everyone logs inside the deferred write, atomically with it.
Run ONLY with the in-memory SQLite env."""
from unittest import mock

from django.conf import settings
from django.test import override_settings

from api.notification.audience import Audience
from api.notification.notification_view import AdminBroadcastDispatchAPI
from api.notification.service import NotificationService
from api.notification.tests.helpers import hit
from api.notification.types import NotificationType
from db.mentor import SystemActionLog
from db.notification import (
    BroadcastNotification,
    BroadcastNotificationRead,
    Notification,
)
from db.user import Role, User, UserRoleLink
from utils.tests.unmanaged_db import UnmanagedDbTestCase, make_user

P = "/api/v1/notification/broadcast/dispatch/"


class DispatchAuditTests(UnmanagedDbTestCase):
    MODELS = [
        User,
        Role,
        UserRoleLink,
        Notification,
        BroadcastNotification,
        BroadcastNotificationRead,
        SystemActionLog,
    ]

    def setUp(self):
        super().setUp()
        make_user("f1", {"Fellow": True})
        make_user("s1", {"Student": True})
        make_user("s2", {"Student": True})
        # Personal rows carry created_by = SYSTEM_ADMIN_ID, an FK to user.
        make_user(settings.SYSTEM_ADMIN_ID)

    def send(self):
        return hit(
            AdminBroadcastDispatchAPI,
            "post",
            P,
            "f1",
            ["Fellow"],
            {"title": "Hi", "description": "All"},
        )

    @override_settings(NOTIFICATION_BROADCAST_THRESHOLD=1)
    def test_send_to_everyone_logs_with_the_broadcast_id(self):
        self.send()
        b = BroadcastNotification.objects.get()
        log = SystemActionLog.objects.get()
        assert (log.action_type, log.entity_id) == ("NOTIF_BROADCAST_SEND", str(b.id))
        assert log.entity_name == "broadcast_notification"
        assert log.new_data["title"] == "Hi"
        assert log.new_data["_audit"]["audience_label"] == "Everyone"
        assert log.new_data["_audit"]["title"] == "Hi"

    @override_settings(NOTIFICATION_BROADCAST_THRESHOLD=1)
    def test_send_to_everyone_logs_the_head_count(self):
        expected = NotificationService._resolver.count(Audience.all(), actor_id="f1")
        assert expected > 0
        self.send()
        log = SystemActionLog.objects.get()
        assert log.new_data["_audit"]["audience_size"] == expected
        assert f"{expected:,} people" in log.remarks

    @override_settings(NOTIFICATION_BROADCAST_THRESHOLD=1000)
    def test_small_audience_logs_personal_rows(self):
        self.send()
        assert Notification.objects.count() > 0
        log = SystemActionLog.objects.get()
        assert log.action_type == "NOTIF_BROADCAST_SEND"
        assert log.entity_name == "notification"
        assert "personal notifications" in log.remarks
        # Head count is the number of people written to.
        assert log.new_data["_audit"]["audience_size"] == Notification.objects.count()
        assert log.new_data["_audit"]["title"] == "Hi"

    @override_settings(NOTIFICATION_BROADCAST_THRESHOLD=1)
    def test_failed_deferred_write_leaves_no_log(self):
        with mock.patch(
            "api.notification.broadcast_utils.BroadcastUtils.create_broadcast",
            side_effect=RuntimeError,
        ):
            try:
                self.send()
            except RuntimeError:
                pass
        assert SystemActionLog.objects.count() == 0

    @override_settings(NOTIFICATION_BROADCAST_THRESHOLD=1)
    def test_log_failure_rolls_back_the_broadcast(self):
        with mock.patch("api.notification.audit.record", side_effect=RuntimeError):
            try:
                self.send()
            except RuntimeError:
                pass
        assert BroadcastNotification.objects.count() == 0
        assert SystemActionLog.objects.count() == 0

    @override_settings(NOTIFICATION_BROADCAST_THRESHOLD=1000)
    def test_log_failure_rolls_back_personal_rows(self):
        with mock.patch("api.notification.audit.record", side_effect=RuntimeError):
            try:
                self.send()
            except RuntimeError:
                pass
        assert Notification.objects.count() == 0
        assert SystemActionLog.objects.count() == 0

    @override_settings(NOTIFICATION_BROADCAST_THRESHOLD=1)
    def test_dispatch_without_audit_writes_no_log(self):
        NotificationService.dispatch(
            notif_type=NotificationType.ADMIN_BROADCAST,
            audience=Audience.all(),
            context={"title": "T", "body": "B"},
            actor_id="f1",
        )
        assert BroadcastNotification.objects.count() == 1
        assert SystemActionLog.objects.count() == 0
