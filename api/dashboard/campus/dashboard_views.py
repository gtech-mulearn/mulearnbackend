from datetime import timedelta

from django.db.models import Count, Max, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView

from api.dashboard.campus.dash_campus_helper import get_user_college_link
from db.learning_circle import CircleMeetingLog, LearningCircle, UserCircleLink
from db.organization import UserOrganizationLink
from db.task import KarmaActivityLog
from db.user import User
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiResponse
from rest_framework import serializers as s


def _campus_context(request):
    user_id = JWTUtils.fetch_user_id(request)
    link = get_user_college_link(user_id)
    if not link:
        return None, CustomResponse(
            general_message="User is not linked to a campus",
            message={"error_code": "CAMPUS_NOT_FOUND"},
        ).get_failure_response(
            status_code=404,
            http_status_code=status.HTTP_404_NOT_FOUND,
        )
    return link.org, None


def _period_start(request, default_days=30):
    period = request.query_params.get("period", f"{default_days}d")
    days = {"7d": 7, "30d": 30, "60d": 60, "90d": 90}.get(period, default_days)
    return timezone.now() - timedelta(days=days)


def _member_funnel(org):
    registered = UserOrganizationLink.objects.filter(org=org).count()
    onboarded = UserOrganizationLink.objects.filter(org=org, verified=True).count()
    active = UserOrganizationLink.objects.filter(
        org=org,
        user__wallet_user__karma_last_updated_at__gte=timezone.now() - timedelta(days=30),
    ).count()
    level_2_plus = UserOrganizationLink.objects.filter(
        org=org,
        user__user_lvl_link_user__level__level_order__gte=2,
    ).count()
    circle_leads = UserCircleLink.objects.filter(
        circle__org=org,
        lead=True,
        accepted=True,
    ).values("user_id").distinct().count()
    max_value = registered or 0

    def stage(key, label, count):
        return {
            "key": key,
            "label": label,
            "count": count,
            "percentage": round((count / max_value) * 100, 2) if max_value else 0,
        }

    return {
        "max": max_value,
        "stages": [
            stage("registered", "Registered", registered),
            stage("onboarded", "Onboarded", onboarded),
            stage("active", "Active", active),
            stage("level_2_plus", "Level 2+", level_2_plus),
            stage("circle_lead", "Circle Lead", circle_leads),
        ],
    }


def _circle_health(org, since):
    circles = LearningCircle.objects.filter(org=org).select_related("ig")
    data = []
    for circle in circles:
        meeting_stats = CircleMeetingLog.objects.filter(
            circle_id=circle,
            meet_time__gte=since,
        ).aggregate(count=Count("id"), last=Max("meet_time"))
        sessions = meeting_stats["count"] or 0
        status_value = "active" if sessions >= 2 else "slow" if sessions == 1 else "inactive"
        data.append({
            "circle_id": str(circle.id),
            "circle_name": circle.title,
            "ig_id": str(circle.ig_id),
            "ig_name": circle.ig.name if circle.ig else None,
            "member_count": UserCircleLink.objects.filter(circle=circle, accepted=True).count(),
            "sessions_per_month": sessions,
            "last_session_at": meeting_stats["last"].isoformat() if meeting_stats["last"] else None,
            "status": status_value,
        })
    return data


def _recent_activity(org, limit):
    activities = []
    for circle in LearningCircle.objects.filter(org=org).select_related("created_by").order_by("-created_at")[:limit]:
        activities.append({
            "id": str(circle.id),
            "type": "circle_created",
            "title": f"{circle.title} created",
            "description": f"{circle.title} was created",
            "created_at": circle.created_at.isoformat() if circle.created_at else None,
            "actor": {
                "id": str(circle.created_by_id),
                "full_name": circle.created_by.full_name if circle.created_by else None,
                "muid": circle.created_by.muid if circle.created_by else None,
                "profile_pic": circle.created_by.profile_pic if circle.created_by else None,
            },
            "metadata": {"circle_id": str(circle.id), "circle_name": circle.title},
        })
    return sorted(activities, key=lambda item: item["created_at"] or "", reverse=True)[:limit]


def _campus_stats(org, since):
    members = UserOrganizationLink.objects.filter(org=org,verified=True)
    active_members = members.filter(user__wallet_user__karma_last_updated_at__gte=since).count()
    total_karma = members.aggregate(total=Sum("user__wallet_user__karma")).get("total") or 0
    active_circles = LearningCircle.objects.filter(org=org).count()
    period_karma = KarmaActivityLog.objects.filter(
        user__user_organization_link_user__org=org,
        created_at__gte=since,
    ).aggregate(total=Sum("karma")).get("total") or 0
    return [
        {"key": "active_members", "label": "Active members", "value": active_members, "delta": active_members, "delta_type": "increase", "period": "30d"},
        {"key": "total_karma", "label": "Karma", "value": total_karma, "delta": period_karma, "delta_type": "increase", "period": "30d"},
        {"key": "active_circles", "label": "Circles", "value": active_circles, "delta": 0, "delta_type": "neutral", "period": "30d"},
        {"key": "rank", "label": "Campus rank", "value": None, "delta": 0, "delta_type": "neutral", "period": "30d"},
    ]


class CampusDashboardSummaryAPIView(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Campus'], description="Retrieve Campus Dashboard Summary.",
        responses={200: inline_serializer(
            name="CampusDashboardSummaryResponse",
            fields={
                "hasError": s.BooleanField(),
                "statusCode": s.IntegerField(),
                "message": s.DictField(),
                "response": inline_serializer(
                    name="CampusDashboardSummaryData",
                    fields={
                        "campus": inline_serializer(
                            name="CampusDashboardSummaryCampus",
                            fields={
                                "org_id": s.CharField(),
                                "college_name": s.CharField(),
                                "campus_code": s.CharField(),
                                "campus_zone": s.CharField(allow_null=True),
                            },
                        ),
                        "stat_cards": inline_serializer(
                            name="CampusDashboardStatCard",
                            fields={
                                "key": s.CharField(),
                                "label": s.CharField(),
                                "value": s.IntegerField(allow_null=True),
                                "delta": s.IntegerField(),
                                "delta_type": s.CharField(),
                                "period": s.CharField(),
                            },
                            many=True,
                        ),
                        "member_funnel": inline_serializer(
                            name="CampusDashboardMemberFunnel",
                            fields={
                                "max": s.IntegerField(),
                                "stages": inline_serializer(
                                    name="CampusDashboardFunnelStage",
                                    fields={
                                        "key": s.CharField(),
                                        "label": s.CharField(),
                                        "count": s.IntegerField(),
                                        "percentage": s.FloatField(),
                                    },
                                    many=True,
                                ),
                            },
                        ),
                        "circle_health": inline_serializer(
                            name="CampusDashboardCircleHealth",
                            fields={
                                "circle_id": s.CharField(),
                                "circle_name": s.CharField(),
                                "ig_id": s.CharField(),
                                "ig_name": s.CharField(allow_null=True),
                                "member_count": s.IntegerField(),
                                "sessions_per_month": s.IntegerField(),
                                "last_session_at": s.CharField(allow_null=True),
                                "status": s.CharField(),
                            },
                            many=True,
                        ),
                        "recent_activity": inline_serializer(
                            name="CampusDashboardRecentActivity",
                            fields={
                                "id": s.CharField(),
                                "type": s.CharField(),
                                "title": s.CharField(),
                                "description": s.CharField(),
                                "created_at": s.CharField(allow_null=True),
                                "actor": s.DictField(),
                                "metadata": s.DictField(),
                            },
                            many=True,
                        ),
                    },
                ),
            },
        )},
    )
    def get(self, request):
        org, error = _campus_context(request)
        if error:
            return error
        since = _period_start(request)
        return CustomResponse(
            general_message="Campus dashboard summary fetched successfully",
            response={
                "campus": {
                    "org_id": str(org.id),
                    "college_name": org.title,
                    "campus_code": org.code,
                    "campus_zone": org.district.zone.name if org.district and org.district.zone else None,
                },
                "stat_cards": _campus_stats(org, since),
                "member_funnel": _member_funnel(org),
                "circle_health": _circle_health(org, since),
                "recent_activity": _recent_activity(org, 10),
            },
        ).get_success_response()


class CampusMemberFunnelAPIView(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Campus'], description="Retrieve Campus Member Funnel.",
        responses={200: inline_serializer(
            name="CampusMemberFunnelResponse",
            fields={
                "hasError": s.BooleanField(),
                "statusCode": s.IntegerField(),
                "message": s.DictField(),
                "response": inline_serializer(
                    name="CampusMemberFunnelData",
                    fields={
                        "max": s.IntegerField(),
                        "stages": inline_serializer(
                            name="CampusMemberFunnelStage",
                            fields={
                                "key": s.CharField(),
                                "label": s.CharField(),
                                "count": s.IntegerField(),
                                "percentage": s.FloatField(),
                            },
                            many=True,
                        ),
                    },
                ),
            },
        )},
    )
    def get(self, request):
        org, error = _campus_context(request)
        if error:
            return error
        return CustomResponse(
            general_message="Campus member funnel fetched successfully",
            response=_member_funnel(org),
        ).get_success_response()


class CampusCircleHealthAPIView(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Campus'], description="Retrieve Campus Circle Health.",
        responses={200: inline_serializer(
            name="CampusCircleHealthResponse",
            fields={
                "hasError": s.BooleanField(),
                "statusCode": s.IntegerField(),
                "message": s.DictField(),
                "response": inline_serializer(
                    name="CampusCircleHealthData",
                    fields={
                        "data": inline_serializer(
                            name="CampusCircleHealthItem",
                            fields={
                                "circle_id": s.CharField(),
                                "circle_name": s.CharField(),
                                "ig_id": s.CharField(),
                                "ig_name": s.CharField(allow_null=True),
                                "member_count": s.IntegerField(),
                                "sessions_per_month": s.IntegerField(),
                                "last_session_at": s.CharField(allow_null=True),
                                "status": s.CharField(),
                            },
                            many=True,
                        ),
                    },
                ),
            },
        )},
    )
    def get(self, request):
        org, error = _campus_context(request)
        if error:
            return error
        return CustomResponse(
            general_message="Campus circle health fetched successfully",
            response={"data": _circle_health(org, _period_start(request))},
        ).get_success_response()


class CampusRecentActivityAPIView(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Campus'], description="Retrieve Campus Recent Activity.",
        responses={200: inline_serializer(
            name="CampusRecentActivityResponse",
            fields={
                "hasError": s.BooleanField(),
                "statusCode": s.IntegerField(),
                "message": s.DictField(),
                "response": inline_serializer(
                    name="CampusRecentActivityData",
                    fields={
                        "data": inline_serializer(
                            name="CampusRecentActivityItem",
                            fields={
                                "id": s.CharField(),
                                "type": s.CharField(),
                                "title": s.CharField(),
                                "description": s.CharField(),
                                "created_at": s.CharField(allow_null=True),
                                "actor": s.DictField(),
                                "metadata": s.DictField(),
                            },
                            many=True,
                        ),
                    },
                ),
            },
        )},
    )
    def get(self, request):
        org, error = _campus_context(request)
        if error:
            return error
        limit = min(int(request.query_params.get("limit", 10)), 50)
        return CustomResponse(
            general_message="Campus recent activity fetched successfully",
            response={"data": _recent_activity(org, limit)},
        ).get_success_response()
