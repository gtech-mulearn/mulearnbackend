from datetime import datetime, timedelta, timezone

from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from db.mentor import SystemActionLog
from db.push import PushCampaign
from db.user import User
from utils.permission import CustomizePermission, verified_role_required
from utils.response import CustomResponse
from utils.types import TEAM_ROLES
from utils.utils import CommonUtils

from .audit import ACTION_LABELS


def _utc_day(value: str) -> datetime:
    """'YYYY-MM-DD' as midnight UTC; ValueError when malformed."""
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)


CAMPAIGN_ENTITY = "push_campaign"
CAMPAIGN_FIELDS = ("status", "target_count", "sent_count", "skipped_count", "failed_count")


def _title(row: SystemActionLog, new_data: dict, old_data: dict, audit: dict) -> str | None:
    if row.action_type == "NOTIF_BROADCAST_DEL_ALL":
        return f"{old_data.get('count', 0)} announcements"
    if row.entity_name == "push_config":
        return "Push settings"
    return new_data.get("title") or old_data.get("title") or audit.get("title")


def _campaigns(rows: list) -> dict:
    """{campaign id: live counts} for the page's campaign rows, in one query.
    Sent, skipped and failed keep changing after the send is logged, so they
    are read from the campaign, not from the log."""
    ids = {row.entity_id for row in rows if row.entity_name == CAMPAIGN_ENTITY}
    if not ids:
        return {}
    return {
        str(c["id"]): {f: c[f] for f in CAMPAIGN_FIELDS}
        for c in PushCampaign.objects.filter(id__in=ids).values("id", *CAMPAIGN_FIELDS)
    }


def _item(row: SystemActionLog, campaigns: dict) -> dict:
    stored_new = row.new_data if isinstance(row.new_data, dict) else {}
    old_data = row.old_data if isinstance(row.old_data, dict) else {}
    audit = stored_new.get("_audit") or {}
    new_data = {k: v for k, v in stored_new.items() if k != "_audit"}
    return {
        "id": row.id,
        "action": row.action_type,
        "label": ACTION_LABELS[row.action_type],
        "actor": {
            "full_name": row.actor_user.full_name,
            "muid": row.actor_user.muid,
        },
        "roles": list(audit.get("roles") or []),
        "title": _title(row, new_data, old_data, audit),
        "entity_name": row.entity_name,
        "entity_id": row.entity_id,
        # Live counts for campaign rows; null for other rows or a campaign
        # that no longer exists.
        "campaign": (
            campaigns.get(row.entity_id) if row.entity_name == CAMPAIGN_ENTITY else None
        ),
        "audience_size": audit.get("audience_size"),
        "audience_label": audit.get("audience_label"),
        "created_at": row.created_at.isoformat(),
        "old_data": row.old_data,
        "new_data": new_data if row.new_data is not None else None,
    }


class ActivityLogAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Notification"],
        description=(
            "Verified team (Admins, Fellows, Associates). Activity log of "
            "announcement and push changes, newest first."
        ),
    )
    @verified_role_required(list(TEAM_ROLES))
    def get(self, request):
        params = request.query_params
        queryset = SystemActionLog.objects.filter(
            action_type__in=ACTION_LABELS.keys()
        ).select_related("actor_user")

        action = params.get("action")
        if action:
            if action not in ACTION_LABELS:
                return CustomResponse(
                    general_message="Unknown action"
                ).get_failure_response()
            queryset = queryset.filter(action_type=action)

        actor = params.get("actor")
        if actor:
            # The column collation folds case and accents, so the exact muid
            # is confirmed in Python before it decides whose rows to show.
            ids = [
                u.id
                for u in User.objects.filter(muid=actor).only("id", "muid")
                if u.muid == actor
            ]
            queryset = queryset.filter(actor_user_id__in=ids)

        try:
            if params.get("from"):
                queryset = queryset.filter(created_at__gte=_utc_day(params["from"]))
            if params.get("to"):
                queryset = queryset.filter(
                    created_at__lt=_utc_day(params["to"]) + timedelta(days=1)
                )
        except ValueError:
            return CustomResponse(
                general_message="Dates must be YYYY-MM-DD"
            ).get_failure_response()

        # '-id' breaks created_at ties, so offset pages never skip or repeat a row.
        paginated = CommonUtils.get_paginated_queryset(
            queryset.order_by("-created_at", "-id"),
            request,
            [],
            {"created_at": "created_at"},
        )
        rows = list(paginated["queryset"])
        campaigns = _campaigns(rows)
        return CustomResponse().paginated_response(
            data=[_item(row, campaigns) for row in rows],
            pagination=paginated["pagination"],
        )
