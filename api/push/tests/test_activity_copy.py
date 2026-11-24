"""Activity push copy: versions, the variant sent with each push, and the
per-version counts on the admin stats endpoint.
Run ONLY with the in-memory SQLite env (see test_push_logic.py)."""
import random
from unittest import mock

from django.test import override_settings

from api.notification.service import NotificationService
from api.notification.templates import TEMPLATES, render_template
from api.notification.tests.helpers import hit
from api.push.sender import Message
from api.push.views import AdminStatsAPI
from db.push import PushConfig, PushDeliveryLog, UserPushDevice
from db.user import Role, User, UserRoleLink
from mu_celery import push_tasks
from utils.tests.unmanaged_db import UnmanagedDbTestCase, make_user

PRODUCER_CONTEXT = {
    "KARMA_AWARDED": {"karma": 20, "reason": "Intro to Git"},
    "LC_JOIN_APPROVED": {"lc_name": "Python Circle"},
    "LC_JOIN_REJECTED": {"lc_name": "Python Circle"},
    "LC_INVITE": {"lc_name": "Python Circle"},
    "LC_MEETING_SCHEDULED": {"lc_name": "Python Circle", "meet_time": "20 Nov 2026, 06:00 PM"},
    "EVENT_CANCELLED": {"event_title": "Figma Jam"},
    "JOB_APPLICATION_STATUS": {"job_title": "Intern", "status": "shortlisted"},
}


def test_every_push_version_renders_with_its_producer_context():
    for t, ctx in PRODUCER_CONTEXT.items():
        variants = TEMPLATES[(t, "PUSH")]["variants"]
        assert len(variants) == 3
        keys = [v["key"] for v in variants]
        assert len(set(keys)) == len(keys)
        for v in variants:
            title, body = v["title"].format(**ctx), v["body"].format(**ctx)
            assert title and body and len(v["title"]) <= 40 and len(v["body"]) <= 100
            assert len(f"{t}:{v['key']}") <= 40


def test_karma_awarded_copy_does_not_claim_a_reviewer():
    # The push also fires for self-awarded karma, so no line may say a
    # reviewer approved it.
    variants = {v["key"]: v for v in TEMPLATES[("KARMA_AWARDED", "PUSH")]["variants"]}
    assert variants["yes"]["title"] == "+{karma} karma ✅"
    assert variants["yes"]["body"] == "That's for {reason}. Keep going."
    for v in variants.values():
        assert "review" not in (v["title"] + v["body"]).lower()


def test_render_template_returns_variant_key():
    out = render_template(
        "KARMA_AWARDED", "PUSH", PRODUCER_CONTEXT["KARMA_AWARDED"], rng=random.Random(0)
    )
    assert out["variant"].startswith("KARMA_AWARDED:")
    assert out["title"] and out["body"]
    assert "{" not in out["title"] + out["body"]


def test_render_template_missing_key_returns_none():
    assert render_template("KARMA_AWARDED", "PUSH", {}) is None


def test_render_template_without_variants_keeps_old_shape():
    out = render_template("KARMA_REMOVED", "IN_APP", {"karma": 5, "reason": "x"})
    assert set(out) == {"title", "body"}


class EnqueueTests(UnmanagedDbTestCase):
    MODELS = [User, Role, UserRoleLink, PushConfig]

    def enqueue(self, notif_type, context, rendered):
        with mock.patch("api.push.fcm.is_configured", return_value=True), mock.patch(
            "api.push.config.push_allowed_for_type", return_value=True
        ), mock.patch("mu_celery.push_tasks.send_activity_push.delay") as delay:
            NotificationService._enqueue_push(
                notif_type, "learning_circle", ["u1"], rendered, context,
                "learning_circle", "e1", "k1", None,
            )
        return delay

    def test_enqueue_push_forwards_variant(self):
        delay = self.enqueue(
            "LC_INVITE", {"lc_name": "Python Circle"}, {"title": "in-app", "body": "in-app"}
        )
        self.assertTrue(delay.call_args.kwargs["variant"].startswith("LC_INVITE:"))
        self.assertNotEqual(delay.call_args.args[3], "in-app")

    def test_enqueue_push_falls_back_to_in_app_text_without_variant(self):
        delay = self.enqueue("LC_INVITE", {}, {"title": "in-app", "body": "in-app text"})
        self.assertEqual(delay.call_args.args[3:5], ("in-app", "in-app text"))
        self.assertIsNone(delay.call_args.kwargs["variant"])


class TaskTests(UnmanagedDbTestCase):
    MODELS = [User, Role, UserRoleLink, PushConfig]

    def test_send_activity_push_passes_variant_and_requeues_with_it(self):
        res = mock.Mock(retry_after=30, deferred=[])
        with mock.patch.object(push_tasks.sender, "deliver", return_value=res) as deliver, \
                mock.patch.object(push_tasks.send_activity_push, "apply_async") as again:
            push_tasks.send_activity_push(
                "LC_INVITE", "learning_circle", ["u1"], "t", "b", None, "k", {}, variant="LC_INVITE:saved"
            )
        self.assertEqual(deliver.call_args.args[2], "LC_INVITE")
        msg = deliver.call_args.args[3]
        self.assertIsInstance(msg, Message)
        self.assertEqual(msg.variant, "LC_INVITE:saved")
        self.assertEqual(again.call_args.kwargs["kwargs"], {"variant": "LC_INVITE:saved"})

    def test_old_queued_message_without_variant_still_runs(self):
        res = mock.Mock(retry_after=0, deferred=[])
        with mock.patch.object(push_tasks.sender, "deliver", return_value=res) as deliver:
            push_tasks.send_activity_push("LC_INVITE", "learning_circle", ["u1"], "t", "b", None, "k", {})
        self.assertIsNone(deliver.call_args.args[3].variant)


class StatsDb(UnmanagedDbTestCase):
    MODELS = [User, Role, UserRoleLink, PushDeliveryLog, UserPushDevice]

    def setUp(self):
        super().setUp()
        self.fellow = make_user("f1", {"Fellow": True})

    def log(self, variant, status="sent", opened=False):
        from django.utils import timezone

        return PushDeliveryLog.objects.create(
            user=self.fellow, source="engagement", kind="STREAK_RESCUE", variant=variant,
            dedupe_key=f"d{PushDeliveryLog.objects.count()}", status=status,
            title="t", body="b", opened_at=timezone.now() if opened else None,
        )

    def test_stats_include_per_variant_counts(self):
        self.log("STREAK_RESCUE:keep", opened=True)
        self.log("STREAK_RESCUE:keep")
        self.log("STREAK_RESCUE:alpha")
        self.log("STREAK_RESCUE:keep", status="skipped_cap")
        self.log(None)
        r = hit(AdminStatsAPI, "get", "/api/v1/push/admin/stats/", "f1", ["Fellow"])
        assert r.data["hasError"] is False, r.data
        self.assertEqual(
            r.data["response"]["variants"],
            [
                {"variant": "STREAK_RESCUE:alpha", "sent": 1, "opened": 0},
                {"variant": "STREAK_RESCUE:keep", "sent": 2, "opened": 1},
            ],
        )
