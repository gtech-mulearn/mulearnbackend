from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView

from db.company import CompanyJob
from db.learning_circle import CircleMeetingLog, UserCircleLink
from db.task import KarmaActivityLog, Wallet
from db.user import User
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s


def _user_rank(user_id):
    wallet = Wallet.objects.filter(user_id=user_id).first()
    karma = wallet.karma if wallet else 0
    return Wallet.objects.filter(karma__gt=karma).count() + 1


def _streak_payload(user):
    activity_dates = list(
        KarmaActivityLog.objects.filter(user=user)
        .dates("created_at", "day", order="DESC")[:30]
    )
    streak_count = 0
    if activity_dates:
        expected = activity_dates[0]
        for activity_date in activity_dates:
            if activity_date == expected:
                streak_count += 1
                expected = expected - timedelta(days=1)
            else:
                break

    return {
        "streak_days": streak_count,
        "last_activity_at": activity_dates[0].isoformat() if activity_dates else None,
        "activity_dates": [d.isoformat() for d in activity_dates],
    }


class LearnerDashboardSummaryAPIView(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Home'], description="Retrieve Learner Dashboard Summary.",
        responses={200: inline_serializer(
            name='HomeLearnerDashboardSummaryResponse',
            fields={
                'stats': inline_serializer(
                    name='HomeLearnerDashboardStats',
                    fields={
                        'weekly_karma': s.IntegerField(),
                        'total_karma': s.IntegerField(),
                        'rank': s.IntegerField(),
                        'active_circles': s.IntegerField(),
                        'streak_days': s.IntegerField(),
                    },
                ),
                'next_meeting': s.JSONField(allow_null=True),
                'quick_action_counts': inline_serializer(
                    name='HomeLearnerQuickActionCounts',
                    fields={
                        'circles': s.IntegerField(),
                        'leaderboard_rank': s.IntegerField(),
                        'job_openings': s.IntegerField(),
                    },
                ),
            },
        )},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).select_related("wallet_user").first()
        if not user:
            return CustomResponse(
                general_message="User not found",
                message={"error_code": "USER_NOT_FOUND"},
            ).get_failure_response(
                status_code=401,
                http_status_code=status.HTTP_401_UNAUTHORIZED,
            )

        since = timezone.now() - timedelta(days=7)
        weekly_karma = (
            KarmaActivityLog.objects.filter(user_id=user_id, created_at__gte=since)
            .aggregate(total=Sum("karma"))
            .get("total")
            or 0
        )
        active_circles = UserCircleLink.objects.filter(
            user_id=user_id,
            accepted=True,
        ).count()
        rank = _user_rank(user_id)
        streak = _streak_payload(user)

        next_meeting = (
            CircleMeetingLog.objects.filter(
                circle_id__user_circle_link_circle__user_id=user_id,
                circle_id__user_circle_link_circle__accepted=True,
                meet_time__gte=timezone.now(),
            )
            .select_related("circle_id")
            .order_by("meet_time")
            .first()
        )

        next_meeting_data = None
        if next_meeting:
            next_meeting_data = {
                "id": str(next_meeting.id),
                "circle_id": str(next_meeting.circle_id_id),
                "circle_name": next_meeting.circle_id.title,
                "title": next_meeting.title,
                "starts_at": next_meeting.meet_time.isoformat(),
                "duration_minutes": next_meeting.duration,
                "meeting_link": next_meeting.meet_link,
                "rsvp_status": "joined",
            }

        return CustomResponse(
            general_message="Learner dashboard summary fetched successfully",
            response={
                "stats": {
                    "weekly_karma": weekly_karma,
                    "total_karma": getattr(getattr(user, "wallet_user", None), "karma", 0),
                    "rank": rank,
                    "active_circles": active_circles,
                    "streak_days": streak["streak_days"],
                },
                "next_meeting": next_meeting_data,
                "quick_action_counts": {
                    "circles": active_circles,
                    "leaderboard_rank": rank,
                    "job_openings": CompanyJob.objects.filter(
                        is_deleted=False,
                        status="Active",
                    ).count(),
                },
            },
        ).get_success_response()


class LearnerStreakAPIView(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Home'], description="Retrieve Learner Streak.",
        responses={200: inline_serializer(
            name='HomeLearnerStreakResponse',
            fields={
                'streak_days': s.IntegerField(),
                'last_activity_at': s.CharField(allow_null=True),
                'activity_dates': s.ListField(child=s.CharField()),
            },
        )},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse(
                general_message="User not found",
                message={"error_code": "USER_NOT_FOUND"},
            ).get_failure_response(
                status_code=401,
                http_status_code=status.HTTP_401_UNAUTHORIZED,
            )

        return CustomResponse(
            general_message="Learner streak fetched successfully",
            response=_streak_payload(user),
        ).get_success_response()
