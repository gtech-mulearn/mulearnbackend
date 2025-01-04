from django.db.models import Sum, F, Value, Count, Q, Prefetch
from django.db.models.functions import Concat, Coalesce
from rest_framework.views import APIView
from . import serializers

from db.organization import Organization, UserOrganizationLink
from db.user import User
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils


class StudentsLeaderboard(APIView):
    def get(self, request):
        students_leaderboard = (
            User.objects.filter(
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                user_role_link_user__role__title=RoleType.STUDENT.value,
                exist_in_guild=True,
            )
            .distinct()
            .select_related("wallet_user")
            .prefetch_related(
                Prefetch(
                    "user_organization_link_user",
                    queryset=UserOrganizationLink.objects.filter(
                        org__org_type=OrganizationType.COLLEGE.value
                    ).select_related("org"),
                    to_attr="colleges",
                )
            )
            .order_by("-wallet_user__karma")[:20]
        )
        serialized_students_leaderboard = serializers.StudentLeaderboardSerializer(
            students_leaderboard, many=True
        )

        return CustomResponse(
            response=serialized_students_leaderboard.data
        ).get_success_response()


class StudentsMonthlyLeaderboard(APIView):
    def get(self, request):
        start_date, end_date = DateTimeUtils.get_start_and_end_of_previous_month()
        student_monthly_leaderboard = (
            User.objects.filter(
                user_role_link_user__role__title=RoleType.STUDENT.value,
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                exist_in_guild=True,
            )
            .annotate(
                institution=F("user_organization_link_user__org__title"),
                total_karma=Coalesce(
                    Sum(
                        "karma_activity_log_user__karma",
                        filter=Q(
                            karma_activity_log_user__created_at__range=(
                                start_date,
                                end_date,
                            )
                        ),
                    ),
                    Value(0),
                ),
            )
            .values(
                "full_name",
                "total_karma",
                "institution",
            )
            .order_by("-total_karma")[:20]
        )
        data = [
            {
                "full_name": student.full_name,
                "total_karma": student.total_karma,
                "institution": student.institution,
            }
            for student in student_monthly_leaderboard
        ]

        return CustomResponse(response=data).get_success_response()


class CollegeLeaderboard(APIView):
    def get(self, request):
        college_leaderboard = (
            Organization.objects.filter(
                org_type=OrganizationType.COLLEGE.value,
                user_organization_link_org__user__user_role_link_user__role__title=RoleType.STUDENT.value,
                user_organization_link_org__user__exist_in_guild=True,
            )
            .distinct()
            .annotate(
                total_students=Count("user_organization_link_org__user"),
                total_karma=Sum("user_organization_link_org__user__wallet_user__karma"),
            )
            .values("code", "title", "total_students", "total_karma")
            .order_by("-total_karma")[:20]
        )

        return CustomResponse(response=college_leaderboard).get_success_response()


class CollegeMonthlyLeaderboard(APIView):
    def get(self, request):
        start_date, end_date = DateTimeUtils.get_start_and_end_of_previous_month()
        college_monthly_leaderboard = (
            Organization.objects.filter(
                org_type=OrganizationType.COLLEGE.value,
                user_organization_link_org__user__karma_activity_log_user__created_at__range=(
                    start_date,
                    end_date,
                ),
                user_organization_link_org__user__karma_activity_log_user__appraiser_approved=True,
            )
            .annotate(
                total_karma=Coalesce(
                    Sum(
                        "user_organization_link_org__user__karma_activity_log_user__karma",
                        filter=Q(
                            user_organization_link_org__user__karma_activity_log_user__created_at__range=(
                                start_date,
                                end_date,
                            )
                        ),
                    ),
                    Value(0),
                ),
                students=Count("user_organization_link_org__user", distinct=True),
                institution=F("title"),
            )
            .values("code", "total_karma", "students")
            .order_by("-total_karma")[:20]
        )

        return CustomResponse(
            response=college_monthly_leaderboard
        ).get_success_response()
