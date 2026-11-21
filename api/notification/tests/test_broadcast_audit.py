"""Announcement endpoints write one SystemActionLog row per change.
Run ONLY with the in-memory SQLite env."""
import uuid
from datetime import timedelta
from unittest import mock

from django.utils import timezone

from api.notification.notification_view import (
    BroadcastNotificationCreateAPI,
    BroadcastNotificationDeleteAllAPI,
    BroadcastNotificationDeleteAPI,
    BroadcastNotificationListAPI,
    BroadcastNotificationUpdateAPI,
)
from api.notification.tests.helpers import hit
from db.mentor import SystemActionLog
from db.notification import BroadcastNotification, BroadcastNotificationRead
from db.user import Role, User, UserRoleLink
from utils.tests.unmanaged_db import UnmanagedDbTestCase, make_user

P = "/api/v1/notification/broadcast/"


def seed(user, title="T", target_type="global", target_id=None, notif_type=None, age=0):
    now = timezone.now()
    return BroadcastNotification.objects.create(
        id=uuid.uuid4(),
        title=title,
        description="D",
        target_type=target_type,
        target_id=target_id,
        notif_type=notif_type,
        created_by=user,
        created_at=now - timedelta(minutes=age),
        expires_at=now + timedelta(days=1),
    )


class BroadcastAuditTests(UnmanagedDbTestCase):
    MODELS = [
        User,
        Role,
        UserRoleLink,
        BroadcastNotification,
        BroadcastNotificationRead,
        SystemActionLog,
    ]

    def setUp(self):
        super().setUp()
        self.f1 = make_user("f1", {"Fellow": True})

    def call(self, view, method, data=None, **kw):
        return hit(view, method, P, "f1", ["Fellow"], data, **kw)

    def test_create_logs_once_with_fellow_role(self):
        res = self.call(
            BroadcastNotificationCreateAPI,
            "post",
            {"title": "T", "description": "D", "expires_at": "2026-12-01T00:00:00Z"},
        )
        assert res.data["hasError"] is False
        log = SystemActionLog.objects.get()
        assert log.action_type == "NOTIF_BROADCAST_CREATE"
        assert log.entity_id == str(BroadcastNotification.objects.get().id)
        assert log.new_data["title"] == "T"
        assert log.new_data["_audit"]["roles"] == ["Fellow"]
        assert log.new_data["_audit"]["title"] == "T"
        assert log.remarks.startswith("Fellow")

    def test_update_logs_only_changed_fields(self):
        b = seed(self.f1)
        self.call(
            BroadcastNotificationUpdateAPI, "patch", {"title": "T2"}, broadcast_id=b.id
        )
        log = SystemActionLog.objects.get()
        assert log.action_type == "NOTIF_BROADCAST_UPDATE"
        assert log.old_data == {"title": "T"}
        assert log.new_data["title"] == "T2"
        assert "description" not in log.new_data
        # The subject is named by its title before the change.
        assert log.new_data["_audit"]["title"] == "T"

    def test_update_that_changes_nothing_writes_no_log(self):
        b = seed(self.f1)
        res = self.call(
            BroadcastNotificationUpdateAPI,
            "patch",
            {
                "title": b.title,
                "description": b.description,
                "url": b.url,
                "expires_at": b.expires_at.isoformat(),
            },
            broadcast_id=b.id,
        )
        assert res.data["hasError"] is False, res.data
        assert res.data["response"]["title"] == b.title
        assert SystemActionLog.objects.count() == 0

    def test_delete_logs_the_deleted_row(self):
        b = seed(self.f1)
        self.call(BroadcastNotificationDeleteAPI, "delete", broadcast_id=b.id)
        log = SystemActionLog.objects.get()
        assert log.action_type == "NOTIF_BROADCAST_DELETE"
        assert log.old_data["title"] == "T"
        assert log.new_data["_audit"]["title"] == "T"
        assert BroadcastNotification.objects.count() == 0

    def test_delete_all_caps_logged_items(self):
        now = timezone.now()
        BroadcastNotification.objects.bulk_create(
            [
                BroadcastNotification(
                    id=uuid.uuid4(),
                    title=f"T{i}",
                    description="D",
                    target_type="global" if i % 2 else "campus",
                    target_id=None if i % 2 else "c1",
                    created_by=self.f1,
                    created_at=now,
                    expires_at=now + timedelta(days=1),
                )
                for i in range(600)
            ]
        )
        self.call(BroadcastNotificationDeleteAllAPI, "delete")
        log = SystemActionLog.objects.get(action_type="NOTIF_BROADCAST_DEL_ALL")
        assert log.old_data["count"] == 600
        assert len(log.old_data["items"]) == 500
        assert log.old_data["truncated"] is True
        assert log.entity_id == "all"
        assert log.new_data["_audit"]["title"] is None

    def test_delete_all_with_nothing_writes_no_log(self):
        res = self.call(BroadcastNotificationDeleteAllAPI, "delete")
        assert res.data["hasError"] is True
        assert SystemActionLog.objects.count() == 0

    def test_failed_validation_writes_no_log(self):
        res = self.call(
            BroadcastNotificationCreateAPI,
            "post",
            {"title": "", "description": "D", "expires_at": "2026-12-01T00:00:00Z"},
        )
        assert res.data["hasError"] is True
        assert SystemActionLog.objects.count() == 0

    def test_log_failure_rolls_back_the_change(self):
        with mock.patch("api.notification.audit.record", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                self.call(
                    BroadcastNotificationCreateAPI,
                    "post",
                    {
                        "title": "T",
                        "description": "D",
                        "expires_at": "2026-12-01T00:00:00Z",
                    },
                )
        assert BroadcastNotification.objects.count() == 0

    def test_list_paginates_only_when_asked(self):
        for i in range(3):
            seed(self.f1, title=f"T{i}", age=i)
        plain = self.call(BroadcastNotificationListAPI, "get")
        assert isinstance(plain.data["response"], list)
        paged = hit(
            BroadcastNotificationListAPI, "get", P + "?page=1&page_size=2",
            "f1", ["Fellow"],
        )
        body = paged.data["response"]
        assert (body["count"], body["page"], body["page_size"]) == (3, 1, 2)
        assert len(body["results"]) == 2
        assert body["results"][0]["title"] == "T0"

    def test_paged_list_breaks_created_at_ties_by_id(self):
        now = timezone.now()
        for n in (1, 2):
            BroadcastNotification.objects.create(
                id=uuid.UUID(int=n), title=f"T{n}", description="D",
                target_type="global", created_by=self.f1, created_at=now,
                expires_at=now + timedelta(days=1),
            )
        paged = hit(
            BroadcastNotificationListAPI, "get", P + "?page=1&page_size=10",
            "f1", ["Fellow"],
        )
        titles = [r["title"] for r in paged.data["response"]["results"]]
        assert titles == ["T2", "T1"]

    def test_list_items_carry_source(self):
        seed(self.f1, title="a")
        seed(self.f1, title="b", target_type="campus", target_id="c1")
        seed(self.f1, title="c", notif_type="EVENT_PUBLISHED")
        seed(self.f1, title="d", notif_type="OFFICE_HOURS_ANNOUNCED")
        rows = self.call(BroadcastNotificationListAPI, "get").data["response"]
        by = {r["title"]: r["source"] for r in rows}
        assert by == {
            "a": "team",
            "b": "learning_circle",
            "c": "event",
            "d": "system",
        }
