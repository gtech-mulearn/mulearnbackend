"""
/api/v1/push/  (docs/push-notifications.md, "API")

Learner endpoints are cheap by design: device registration is one upsert and
writes last_seen_at at most once an hour; nothing here sends a push inline.
Admin endpoints require the Admins role.
"""
from datetime import datetime, timedelta, timezone as dt_timezone

from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from rest_framework.views import APIView

from api.push import audience as push_audience
from api.push import config as push_config
from api.push import fcm
from api.push.policy import zone
from db.push import (
    PushCampaign,
    PushDeliveryLog,
    UserPushDevice,
    UserPushPreference,
)
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType

SEEN_WRITE_INTERVAL = timedelta(hours=1)
PLATFORMS = {c.value for c in UserPushDevice.Platform}


def _now():
    return datetime.now(dt_timezone.utc)


def _fail(message, code=400):
    return CustomResponse(general_message=message).get_failure_response(http_status_code=code)


def _ok(response=None, message=None):
    return CustomResponse(
        general_message=message or [], response=response or {}
    ).get_success_response()


def _valid_tz(name):
    if not name:
        return None
    return name if zone(name, fallback="UTC").key == name else None


class DeviceAPI(APIView):
    permission_classes = [CustomizePermission]

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        token = (request.data.get("token") or "").strip()
        platform = (request.data.get("platform") or "").strip().lower()
        if not token or len(token) > 255:
            return _fail("A device token is required.")
        if platform not in PLATFORMS:
            return _fail(f"platform must be one of {sorted(PLATFORMS)}.")
        app_version = (request.data.get("app_version") or "")[:20] or None
        tz = _valid_tz((request.data.get("timezone") or "").strip())
        now = _now()

        device = UserPushDevice.objects.filter(token=token).first()
        if device is None:
            try:
                with transaction.atomic():
                    UserPushDevice.objects.create(
                        user_id=user_id, token=token, platform=platform,
                        app_version=app_version, timezone=tz,
                        is_active=True, last_seen_at=now,
                    )
            except IntegrityError:
                # Registered concurrently by a parallel request: fall through
                # to the update below.
                device = UserPushDevice.objects.filter(token=token).first()
        if device is not None:
            changed = {}
            # A token belongs to whoever registered it last (shared phones).
            if device.user_id != user_id:
                changed["user_id"] = user_id
            if not device.is_active:
                changed.update(is_active=True, failure_count=0)
            if device.app_version != app_version:
                changed["app_version"] = app_version
            if tz and device.timezone != tz:
                changed["timezone"] = tz
            if now - device.last_seen_at >= SEEN_WRITE_INTERVAL or changed:
                changed["last_seen_at"] = now
            if changed:
                UserPushDevice.objects.filter(id=device.id).update(**changed, updated_at=now)
        return _ok({"registered": True})

    def delete(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        token = (request.data.get("token") or request.query_params.get("token") or "").strip()
        if not token:
            return _fail("A device token is required.")
        UserPushDevice.objects.filter(token=token, user_id=user_id).update(is_active=False)
        return _ok({"unregistered": True})


class OpenedAPI(APIView):
    """The app reports a tapped push: feeds the fatigue rule and stats."""

    permission_classes = [CustomizePermission]

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        key = (request.data.get("dedupe_key") or "").strip()
        if not key:
            return _fail("dedupe_key is required.")
        PushDeliveryLog.objects.filter(
            user_id=user_id, dedupe_key=key, opened_at__isnull=True
        ).update(opened_at=_now())
        return _ok()


PREF_FIELDS = ("push_enabled", "engagement_enabled", "muted_categories",
               "quiet_start", "quiet_end", "timezone")


def _pref_dict(pref, defaults):
    if pref is None:
        return {
            "push_enabled": True,
            "engagement_enabled": True,
            "muted_categories": [],
            "quiet_start": defaults["default_quiet_start"],
            "quiet_end": defaults["default_quiet_end"],
            "timezone": defaults["default_timezone"],
        }
    return {f: getattr(pref, f) for f in PREF_FIELDS}


class PreferenceAPI(APIView):
    permission_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        g = push_config.get_config()["global"]
        pref = UserPushPreference.objects.filter(user_id=user_id).first()
        return _ok(_pref_dict(pref, g))

    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        g = push_config.get_config()["global"]
        data = request.data
        current = _pref_dict(UserPushPreference.objects.filter(user_id=user_id).first(), g)
        for flag in ("push_enabled", "engagement_enabled"):
            if flag in data:
                if not isinstance(data[flag], bool):
                    return _fail(f"{flag} must be true or false.")
                current[flag] = data[flag]
        if "muted_categories" in data:
            muted = data["muted_categories"]
            if not isinstance(muted, list) or not all(isinstance(c, str) for c in muted):
                return _fail("muted_categories must be a list of category names.")
            current["muted_categories"] = sorted(set(muted))[:20]
        for hour in ("quiet_start", "quiet_end"):
            if hour in data:
                if not isinstance(data[hour], int) or not 0 <= data[hour] <= 23:
                    return _fail(f"{hour} must be an hour from 0 to 23.")
                current[hour] = data[hour]
        if "timezone" in data:
            tz = _valid_tz(data["timezone"])
            if not tz:
                return _fail("timezone must be an IANA name like Asia/Kolkata.")
            current["timezone"] = tz
        UserPushPreference.objects.update_or_create(user_id=user_id, defaults=current)
        return _ok(current, "Notification settings saved.")


# ── Admin ────────────────────────────────────────────────────────────────────

GLOBAL_LIMITS = {
    "daily_cap": (0, 50),
    "engagement_daily_cap": (0, 10),
    "max_per_minute": (60, 60000),
    "default_quiet_start": (0, 23),
    "default_quiet_end": (0, 23),
    "nudge_window_start": (0, 23),
    "nudge_window_end": (1, 24),
    "fatigue_lookback_days": (1, 60),
    "max_backoff_days": (1, 60),
    "chunk_size": (50, 5000),
}


class AdminConfigAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        config = push_config.get_config()
        from api.notification.types import TYPE_META

        types = {
            str(getattr(t, "value", t)): push_config.push_allowed_for_type(
                config, str(getattr(t, "value", t)), meta.eligible)
            for t, meta in TYPE_META.items() if "PUSH" in meta.eligible
        }
        return _ok({
            "configured": fcm.is_configured(),
            "global": config["global"],
            "rules": config["rules"],
            "types": types,
        })

    @role_required([RoleType.ADMIN.value])
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        data = request.data
        if "global" in data:
            patch = data["global"]
            if not isinstance(patch, dict):
                return _fail("global must be an object.")
            clean = {}
            for k, v in patch.items():
                if k == "kill_switch":
                    if not isinstance(v, bool):
                        return _fail("kill_switch must be true or false.")
                    clean[k] = v
                elif k == "default_timezone":
                    if not _valid_tz(v):
                        return _fail("default_timezone must be an IANA name.")
                    clean[k] = v
                elif k in GLOBAL_LIMITS:
                    lo, hi = GLOBAL_LIMITS[k]
                    if not isinstance(v, int) or not lo <= v <= hi:
                        return _fail(f"{k} must be a whole number from {lo} to {hi}.")
                    clean[k] = v
                else:
                    return _fail(f"Unknown setting: {k}.")
            stored = _stored("global")
            push_config.set_config("global", {**stored, **clean}, user_id)
        if "rules" in data:
            rules = data["rules"]
            if not isinstance(rules, dict):
                return _fail("rules must be an object.")
            for key, patch in rules.items():
                default = push_config.DEFAULT_RULES.get(key)
                if default is None or not isinstance(patch, dict):
                    return _fail(f"Unknown rule: {key}.")
                for k, v in patch.items():
                    if k not in default:
                        return _fail(f"Unknown setting for {key}: {k}.")
                    if type(v) is not type(default[k]):
                        return _fail(f"{key}.{k} has the wrong type.")
                stored = _stored(f"rule:{key}")
                push_config.set_config(f"rule:{key}", {**stored, **patch}, user_id)
        if "types" in data:
            types = data["types"]
            if not isinstance(types, dict) or not all(isinstance(v, bool) for v in types.values()):
                return _fail("types must map notification types to true or false.")
            stored = _stored("types")
            push_config.set_config("types", {**stored, **types}, user_id)
        return self.get(request)


def _stored(key):
    from db.push import PushConfig

    row = PushConfig.objects.filter(key=key).first()
    return dict(row.value) if row else {}


def _campaign_dict(c):
    return {
        "id": c.id, "title": c.title, "body": c.body, "route": c.route,
        "audience": c.audience, "status": c.status,
        "scheduled_at": c.scheduled_at, "respect_quiet_hours": c.respect_quiet_hours,
        "target_count": c.target_count, "sent_count": c.sent_count,
        "skipped_count": c.skipped_count, "failed_count": c.failed_count,
        "created_at": c.created_at, "sent_at": c.sent_at,
        "created_by": c.created_by.full_name if c.created_by_id else None,
    }


def _route_ok(route):
    return route is None or (isinstance(route, str) and route.startswith("/") and len(route) <= 255)


class AdminCampaignAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        rows = PushCampaign.objects.select_related("created_by").order_by("-created_at")[:100]
        return _ok({"campaigns": [_campaign_dict(c) for c in rows]})

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        d = request.data
        title = (d.get("title") or "").strip()
        body = (d.get("body") or "").strip()
        route = (d.get("route") or "").strip() or None
        if not 1 <= len(title) <= 100:
            return _fail("Title is required (up to 100 characters).")
        if not 1 <= len(body) <= 240:
            return _fail("Message is required (up to 240 characters).")
        if not _route_ok(route):
            return _fail("Link must be an app path like /events or /tasks.")
        try:
            aud = push_audience.validate(d.get("audience") or {"type": "all"})
        except push_audience.AudienceError as e:
            return _fail(str(e))
        scheduled_at = d.get("scheduled_at")
        when = None
        if scheduled_at:
            try:
                when = datetime.fromisoformat(str(scheduled_at).replace("Z", "+00:00"))
            except ValueError:
                return _fail("scheduled_at must be an ISO date-time.")
            if when.tzinfo is None:
                return _fail("scheduled_at must include a time zone.")
            if when < _now() - timedelta(minutes=1):
                return _fail("scheduled_at is in the past.")
        campaign = PushCampaign.objects.create(
            title=title, body=body, route=route, audience=aud,
            status="scheduled" if when else "draft",
            scheduled_at=when,
            respect_quiet_hours=bool(d.get("respect_quiet_hours", True)),
            target_count=push_audience.count(aud),
            created_by_id=user_id,
        )
        return _ok(_campaign_dict(campaign), "Campaign saved.")


class AdminCampaignActionAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def post(self, request, campaign_id, action):
        campaign = PushCampaign.objects.filter(id=campaign_id).first()
        if not campaign:
            return _fail("Campaign not found.", 404)
        if action == "send":
            if not fcm.is_configured():
                return _fail("Push is not configured on this server (FIREBASE_CREDENTIALS).")
            from mu_celery.push_tasks import start_campaign

            if not start_campaign(campaign.id):
                return _fail(f"This campaign is already {campaign.status}.")
            return _ok({"status": "sending"}, "Sending started.")
        if action == "cancel":
            n = PushCampaign.objects.filter(
                id=campaign.id, status__in=["draft", "scheduled", "sending"]
            ).update(status="cancelled")
            if not n:
                return _fail(f"This campaign is already {campaign.status}.")
            return _ok({"status": "cancelled"}, "Campaign cancelled.")
        return _fail("Unknown action.", 404)


class AdminTestAPI(APIView):
    """Send a push to the admin's own devices, to check copy and links."""

    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        title = (request.data.get("title") or "Test push").strip()[:100]
        body = (request.data.get("body") or "Push notifications work on this device.").strip()[:240]
        route = (request.data.get("route") or "").strip() or None
        if not _route_ok(route):
            return _fail("Link must be an app path like /events or /tasks.")
        if not fcm.is_configured():
            return _fail("Push is not configured on this server (FIREBASE_CREDENTIALS).")
        from api.push import sender

        result = sender.deliver(
            [user_id], "test", "TEST",
            sender.Message(title=title, body=body, route=route),
            f"TEST:{_now():%Y%m%d%H%M%S}",
        )
        if result.sent:
            return _ok(result.as_dict(), "Test push sent to your devices.")
        return _fail("No push was sent: register this account on a phone first "
                     f"({result.as_dict()}).")


class AdminStatsAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        days = min(max(int(request.query_params.get("days", 14) or 14), 1), 90)
        since = _now() - timedelta(days=days)
        rows = (
            PushDeliveryLog.objects.filter(created_at__gte=since)
            .values("source", "kind", "status")
            .annotate(n=Count("id"), opened=Count("id", filter=Q(opened_at__isnull=False)))
            .order_by("source", "kind", "status")
        )
        devices = UserPushDevice.objects.filter(is_active=True).aggregate(
            devices=Count("id"), users=Count("user_id", distinct=True)
        )
        return _ok({"days": days, "devices": devices, "rows": list(rows)})
