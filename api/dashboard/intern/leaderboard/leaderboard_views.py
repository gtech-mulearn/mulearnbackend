from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType

from .scoring import ranked_members


class InternLeaderboardAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value, RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "The intern leaderboard, best first, paginated with `page` and `page_size` (default "
            "10, at most 100), not pageIndex / perPage: existing clients send these, so this "
            "endpoint deliberately keeps its own pager over the ranked list. Ranks current team members who aren't INACTIVE. score = timesheets x 25 + sum of "
            "karma_awarded x complexity weight (LOW 1, MEDIUM 2, HIGH 3, CRITICAL 5) over verified "
            "tasks, all time."
        ),
        responses={200: OpenApiResponse(description="Paginated leaderboard data with rank and score.")},
    )
    def get(self, request):
        rows = ranked_members()

        # Deliberately not CommonUtils.get_paginated_queryset: this endpoint has always
        # paginated with page / page_size, and changing it would break existing clients.
        try:
            page = max(int(request.GET.get('page', 1)), 1)
            page_size = min(max(int(request.GET.get('page_size', 10)), 1), 100)
        except ValueError:
            return CustomResponse(general_message="page and page_size must be numbers.").get_failure_response()
        start = (page - 1) * page_size
        end = start + page_size

        return CustomResponse(
            response={
                "data": rows[start:end],
                "pagination": {
                    "count": len(rows),
                    "totalPages": (len(rows) + page_size - 1) // page_size,
                    "isNext": end < len(rows),
                    "isPrev": start > 0,
                    "nextPage": page + 1 if end < len(rows) else None
                }
            }
        ).get_success_response()


class InternLeaderboardMeAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="The caller's rank, score and daily and weekly streaks on the leaderboard (same ranking as intern/leaderboard/).",
        responses={200: OpenApiResponse(description="Intern rank and score.")},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        row = next((row for row in ranked_members() if str(row["user_id"]) == str(user_id)), None)
        if row is None:
            return CustomResponse(general_message="Not found in leaderboard.").get_failure_response()
        return CustomResponse(response={
            "rank": row["rank"], "score": row["score"],
            "daily_streak": row["daily_streak"], "weekly_streak": row["weekly_streak"],
        }).get_success_response()
