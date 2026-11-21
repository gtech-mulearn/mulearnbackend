"""Verified Admins, Fellows and Associates may run announcements and pushes;
only Admins may change engine settings. Run ONLY with the in-memory SQLite env."""
from api.notification.notification_view import BroadcastNotificationListAPI
from api.notification.tests.helpers import hit
from api.push.views import (
    AdminCampaignAPI,
    AdminConfigAPI,
    AdminStatsAPI,
)
from db.mentor import SystemActionLog
from db.notification import BroadcastNotification, BroadcastNotificationRead
from db.push import (
    PushCampaign,
    PushConfig,
    PushDeliveryLog,
    UserPushDevice,
)
from db.user import Role, User, UserRoleLink
from utils.tests.unmanaged_db import UnmanagedDbTestCase, make_user

TEAM_GETS = [
    (BroadcastNotificationListAPI, "/api/v1/notification/broadcast/list/all/"),
    (AdminCampaignAPI, "/api/v1/push/admin/campaigns/"),
    (AdminStatsAPI, "/api/v1/push/admin/stats/"),
    (AdminConfigAPI, "/api/v1/push/admin/config/"),
]


class TeamAccessTests(UnmanagedDbTestCase):
    MODELS = [
        User,
        Role,
        UserRoleLink,
        BroadcastNotification,
        BroadcastNotificationRead,
        PushCampaign,
        PushConfig,
        PushDeliveryLog,
        UserPushDevice,
        SystemActionLog,
    ]

    def test_verified_associate_can_read_every_team_list(self):
        make_user("as1", {"Associate": True})
        for view, path in TEAM_GETS:
            assert hit(view, "get", path, "as1", ["Associate"]).data["hasError"] is False, view

    def test_unverified_fellow_is_refused_everywhere(self):
        make_user("f1", {"Fellow": False})
        for view, path in TEAM_GETS:
            assert hit(view, "get", path, "f1", ["Fellow"]).data["hasError"] is True, view

    def test_verified_fellow_can_create_a_campaign(self):
        make_user("f2", {"Fellow": True})
        r = hit(
            AdminCampaignAPI, "post", "/api/v1/push/admin/campaigns/", "f2", ["Fellow"],
            {"title": "Hi", "body": "There", "audience": {"type": "all"}},
        )
        assert r.data["hasError"] is False and PushCampaign.objects.count() == 1

    def test_fellow_cannot_change_engine_settings(self):
        make_user("f3", {"Fellow": True})
        r = hit(
            AdminConfigAPI, "patch", "/api/v1/push/admin/config/", "f3", ["Fellow"],
            {"global": {"daily_cap": 2}},
        )
        assert r.data["hasError"] is True and PushConfig.objects.count() == 0

    def test_verified_admin_can_change_engine_settings(self):
        make_user("a1", {"Admins": True})
        r = hit(
            AdminConfigAPI, "patch", "/api/v1/push/admin/config/", "a1", ["Admins"],
            {"global": {"daily_cap": 2}},
        )
        assert r.data["hasError"] is False
