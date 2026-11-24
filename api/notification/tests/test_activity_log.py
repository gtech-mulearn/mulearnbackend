"""GET /api/v1/notification/activity-log/. Run ONLY with the in-memory SQLite env."""
import uuid
from datetime import datetime, timedelta, timezone as dt_tz
from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from django.urls import resolve
from django.utils import timezone

from api.notification import audit
from api.notification.activity_log_view import ActivityLogAPI
from api.notification.notification_view import BroadcastNotificationUpdateAPI
from api.notification.tests.helpers import hit
from api.push.views import AdminCampaignActionAPI, AdminCampaignAPI
from db.mentor import SystemActionLog
from db.notification import BroadcastNotification, BroadcastNotificationRead
from db.push import (
    PushCampaign,
    PushConfig,
    PushDeliveryLog,
    UserPushDevice,
    UserPushPreference,
)
from db.user import Role, User, UserRoleLink
from utils.tests.unmanaged_db import UnmanagedDbTestCase, make_user

PATH = "/api/v1/notification/activity-log/"
CHUNK = "mu_celery.push_tasks.send_campaign_chunk.delay"


def _log(actor, action, new_data=None, old_data=None, day=None, **kwargs):
    row = SystemActionLog.objects.create(
        action_type=action,
        actor_user_id=actor,
        entity_name=kwargs.get("entity_name", "broadcast_notification"),
        entity_id=kwargs.get("entity_id", "x"),
        old_data=old_data,
        new_data=new_data,
        **({"id": kwargs["id"]} if "id" in kwargs else {}),
    )
    if day:
        SystemActionLog.objects.filter(pk=row.pk).update(
            created_at=datetime.fromisoformat(day).replace(tzinfo=dt_tz.utc)
        )
    return row


def _campaign(title="C", **counts):
    return PushCampaign.objects.create(title=title, body="B", audience={"type": "all"}, **counts)


class ActivityLogTests(UnmanagedDbTestCase):
    MODELS = [User, Role, UserRoleLink, SystemActionLog, PushCampaign]

    def get(self, params=None, user="a1", roles=("Admins",)):
        return hit(ActivityLogAPI, "get", PATH, user, list(roles), params or {})

    def test_lists_only_notification_actions_newest_first(self):
        make_user("a1", {"Admins": True})
        _log("a1", "MENTOR_VERIFY", day="2026-11-01T10:00:00")
        _log("a1", "NOTIF_BROADCAST_CREATE", {"title": "Old"}, day="2026-11-02T10:00:00")
        _log("a1", "PUSH_CAMPAIGN_SEND", {"title": "New"}, day="2026-11-03T10:00:00")
        r = self.get()
        assert r.data["hasError"] is False
        items = r.data["response"]["data"]
        assert [i["action"] for i in items] == ["PUSH_CAMPAIGN_SEND", "NOTIF_BROADCAST_CREATE"]
        assert r.data["response"]["pagination"]["count"] == 2

    def test_filters_by_action_actor_and_dates(self):
        make_user("a1", {"Admins": True})
        make_user("f1", {"Fellow": True})
        _log("a1", "NOTIF_BROADCAST_CREATE", day="2026-11-01T00:00:00")
        _log("f1", "NOTIF_BROADCAST_CREATE", day="2026-11-05T23:59:59")
        _log("f1", "PUSH_CAMPAIGN_SEND", day="2026-11-06T00:00:00")

        by_action = self.get({"action": "PUSH_CAMPAIGN_SEND"}).data["response"]["data"]
        assert [i["action"] for i in by_action] == ["PUSH_CAMPAIGN_SEND"]

        by_actor = self.get({"actor": "f1@mulearn"}).data["response"]["data"]
        assert len(by_actor) == 2
        assert {i["actor"]["muid"] for i in by_actor} == {"f1@mulearn"}
        assert self.get({"actor": "nobody@mulearn"}).data["response"]["data"] == []

        window = self.get({"from": "2026-11-05", "to": "2026-11-05"}).data["response"]["data"]
        assert len(window) == 1 and window[0]["actor"]["muid"] == "f1@mulearn"
        assert len(self.get({"from": "2026-11-05"}).data["response"]["data"]) == 2
        assert len(self.get({"to": "2026-11-01"}).data["response"]["data"]) == 1

    def test_unknown_action_is_rejected(self):
        make_user("a1", {"Admins": True})
        assert self.get({"action": "MENTOR_VERIFY"}).data["hasError"] is True
        assert self.get({"action": "nope"}).data["hasError"] is True

    def test_malformed_date_is_rejected(self):
        make_user("a1", {"Admins": True})
        assert self.get({"from": "05-11-2026"}).data["hasError"] is True
        assert self.get({"to": "tomorrow"}).data["hasError"] is True

    def test_item_shape(self):
        make_user("a1", {"Admins": True})
        campaign = _campaign(
            "Hello", status="sending", target_count=12,
            sent_count=7, skipped_count=3, failed_count=1,
        )
        # Written by the real writer, exactly as the send action writes it.
        row = audit.record(
            audit.AuditSpec("PUSH_CAMPAIGN_SEND", "a1", audience_size=12, title="Hello"),
            entity_name="push_campaign", entity_id=campaign.id,
        )
        item = self.get().data["response"]["data"][0]
        assert item == {
            "id": str(row.id),
            "action": "PUSH_CAMPAIGN_SEND",
            "label": "Sent push campaign",
            "actor": {"full_name": "a1", "muid": "a1@mulearn"},
            "roles": ["Admins"],
            "title": "Hello",
            "entity_name": "push_campaign",
            "entity_id": campaign.id,
            "campaign": {
                "status": "sending",
                "target_count": 12,
                "sent_count": 7,
                "skipped_count": 3,
                "failed_count": 1,
            },
            "audience_size": 12,
            "audience_label": None,
            "created_at": item["created_at"],
            "old_data": None,
            "new_data": {},
        }
        assert isinstance(item["created_at"], str)

    def test_campaign_is_null_for_other_rows_and_gone_campaigns(self):
        make_user("a1", {"Admins": True})
        live = _campaign(status="sent", target_count=4, sent_count=4)
        _log("a1", "PUSH_CAMPAIGN_SEND", entity_name="push_campaign",
             entity_id=live.id, day="2026-11-03T00:00:00")
        _log("a1", "PUSH_CAMPAIGN_CANCEL", entity_name="push_campaign",
             entity_id=str(uuid.uuid4()), day="2026-11-02T00:00:00")
        _log("a1", "NOTIF_BROADCAST_CREATE", {"title": "A"}, entity_id="b1",
             day="2026-11-01T00:00:00")
        items = self.get().data["response"]["data"]
        assert [i["campaign"] for i in items] == [
            {"status": "sent", "target_count": 4, "sent_count": 4,
             "skipped_count": 0, "failed_count": 0},
            None,
            None,
        ]
        assert [(i["entity_name"], i["entity_id"]) for i in items][2] == (
            "broadcast_notification", "b1",
        )

    def test_same_second_rows_have_a_stable_order(self):
        make_user("a1", {"Admins": True})
        same = "2026-11-03T10:00:00"
        _log("a1", "NOTIF_BROADCAST_CREATE", id="00000000-0000-0000-0000-000000000001", day=same)
        _log("a1", "NOTIF_BROADCAST_CREATE", id="00000000-0000-0000-0000-000000000002", day=same)
        ids = [i["id"] for i in self.get().data["response"]["data"]]
        assert ids == [
            "00000000-0000-0000-0000-000000000002",
            "00000000-0000-0000-0000-000000000001",
        ]

    def test_titles_for_delete_all_config_test_and_old_data(self):
        make_user("a1", {"Admins": True})
        _log("a1", "NOTIF_BROADCAST_DEL_ALL", old_data={"count": 3, "items": [], "truncated": False},
             entity_id="all", day="2026-11-01T01:00:00")
        _log("a1", "PUSH_CONFIG_UPDATE", {"global": {}}, entity_name="push_config",
             entity_id="config", day="2026-11-02T01:00:00")
        _log("a1", "PUSH_TEST_SEND", {"title": "Ping"}, entity_name="push_test",
             day="2026-11-03T01:00:00")
        _log("a1", "NOTIF_BROADCAST_DELETE", old_data={"title": "Gone"}, day="2026-11-04T01:00:00")
        _log("a1", "NOTIF_BROADCAST_CREATE", None, day="2026-11-05T01:00:00")
        titles = {i["action"]: i["title"] for i in self.get().data["response"]["data"]}
        assert titles == {
            "NOTIF_BROADCAST_DEL_ALL": "3 announcements",
            "PUSH_CONFIG_UPDATE": "Push settings",
            "PUSH_TEST_SEND": "Ping",
            "NOTIF_BROADCAST_DELETE": "Gone",
            "NOTIF_BROADCAST_CREATE": None,
        }
        no_audit = [i for i in self.get().data["response"]["data"] if i["action"] == "NOTIF_BROADCAST_CREATE"][0]
        assert no_audit["roles"] == [] and no_audit["new_data"] is None

    def test_unverified_fellow_is_refused(self):
        make_user("f1", {"Fellow": False})
        assert self.get(user="f1", roles=("Fellow",)).data["hasError"] is True

    def test_page_costs_a_constant_number_of_queries(self):
        # Role check, count, page, and one campaign lookup for the whole page.
        make_user("a1", {"Admins": True})
        for n in range(5):
            _log("a1", "NOTIF_BROADCAST_CREATE", {"title": str(n)})
        for n in range(2):
            _log("a1", "PUSH_CAMPAIGN_SEND", entity_name="push_campaign",
                 entity_id=_campaign(str(n)).id)
        with self.assertNumQueries(4):
            self.get({"perPage": 20})
        for n in range(6):
            _log("a1", "PUSH_CAMPAIGN_CANCEL", entity_name="push_campaign",
                 entity_id=_campaign(str(n)).id)
        cache.clear()  # the role check is cached; measure the same work again
        with self.assertNumQueries(4):
            self.get({"perPage": 20})

    def test_url_resolves_to_activity_log_not_delete_one(self):
        assert resolve(PATH).func.view_class is ActivityLogAPI


@override_settings(FIREBASE_CREDENTIALS='{"x": 1}', PUSH_ENABLED=True)
class ActivityTitlesFromRealWritesTests(UnmanagedDbTestCase):
    """Every log row names its subject, as written by the real endpoints."""

    MODELS = [
        User,
        Role,
        UserRoleLink,
        SystemActionLog,
        BroadcastNotification,
        BroadcastNotificationRead,
        PushCampaign,
        PushConfig,
        PushDeliveryLog,
        UserPushDevice,
        UserPushPreference,
    ]

    def setUp(self):
        super().setUp()
        make_user("f1", {"Fellow": True})

    def items(self):
        r = hit(ActivityLogAPI, "get", PATH, "f1", ["Fellow"], {})
        assert r.data["hasError"] is False, r.data
        return {i["action"]: i for i in r.data["response"]["data"]}

    def test_campaign_send_and_cancel_name_the_campaign(self):
        r = hit(
            AdminCampaignAPI, "post", "/api/v1/push/admin/campaigns/", "f1", ["Fellow"],
            {"title": "Diwali coding night", "body": "Starts 7 pm", "audience": {"type": "all"}},
        )
        cid = r.data["response"]["id"]
        with mock.patch(CHUNK):
            for action in ("send", "cancel"):
                res = hit(
                    AdminCampaignActionAPI, "post", "/api/v1/push/admin/campaigns/",
                    "f1", ["Fellow"], campaign_id=cid, action=action,
                )
                assert res.data["hasError"] is False, res.data
        campaign = PushCampaign.objects.get(id=cid)
        items = self.items()
        for action in ("PUSH_CAMPAIGN_CREATE", "PUSH_CAMPAIGN_SEND", "PUSH_CAMPAIGN_CANCEL"):
            item = items[action]
            assert item["title"] == campaign.title, action
            assert (item["entity_name"], item["entity_id"]) == ("push_campaign", cid), action
            assert item["campaign"] == {
                "status": "cancelled",
                "target_count": campaign.target_count,
                "sent_count": 0,
                "skipped_count": 0,
                "failed_count": 0,
            }, action

    def test_edit_that_keeps_the_title_is_named_by_it(self):
        now = timezone.now()
        b = BroadcastNotification.objects.create(
            id=uuid.uuid4(), title="Hackathon week", description="Old text",
            target_type="global", created_by_id="f1", created_at=now,
            expires_at=now + timedelta(days=1),
        )
        res = hit(
            BroadcastNotificationUpdateAPI, "patch", "/api/v1/notification/broadcast/",
            "f1", ["Fellow"], {"description": "New text"}, broadcast_id=b.id,
        )
        assert res.data["hasError"] is False, res.data
        item = self.items()["NOTIF_BROADCAST_UPDATE"]
        assert item["title"] == "Hackathon week"
        assert item["new_data"] == {"description": "New text"}
        assert (item["entity_name"], item["entity_id"], item["campaign"]) == (
            "broadcast_notification", str(b.id), None,
        )

    def test_edit_that_renames_shows_the_new_title(self):
        now = timezone.now()
        b = BroadcastNotification.objects.create(
            id=uuid.uuid4(), title="Old name", description="D",
            target_type="global", created_by_id="f1", created_at=now,
            expires_at=now + timedelta(days=1),
        )
        hit(
            BroadcastNotificationUpdateAPI, "patch", "/api/v1/notification/broadcast/",
            "f1", ["Fellow"], {"title": "New name"}, broadcast_id=b.id,
        )
        assert self.items()["NOTIF_BROADCAST_UPDATE"]["title"] == "New name"
