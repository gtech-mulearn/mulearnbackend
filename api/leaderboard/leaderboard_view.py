from django.db.models import Sum, F, Value, Count, Q, Prefetch
from django.db.models.functions import Concat, Coalesce
from rest_framework.views import APIView
from . import serializers
from db.task import TaskList
from db.organization import Organization, UserOrganizationLink
from db.user import User, UserRoleLink
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils
from drf_spectacular.utils import extend_schema
from utils.schema_utils import CustomResponseSerializer


class StudentsLeaderboard(APIView):
    @extend_schema(
        tags=['Leaderboard'],
        description="Retrieve Students Leaderboard.",
        responses={200: serializers.StudentLeaderboardSerializer},
    )
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
    @extend_schema(tags=['Leaderboard'], description="Retrieve Students Monthly Leaderboard.",
        responses={200: CustomResponseSerializer},
    )
    def get(self, request):
        start_date, end_date = DateTimeUtils.get_start_and_end_of_previous_month()
        print("REquest reeceivd")
        student_monthly_leaderboard = (
            User.objects.prefetch_related(
                "user_role_link_user__role",
                "user_organization_link_user__org",
                "karma_activity_log_user",
            )
            .filter(
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

        return CustomResponse(
            response=student_monthly_leaderboard
        ).get_success_response()


class CollegeLeaderboard(APIView):
    @extend_schema(tags=['Leaderboard'], description="Retrieve College Leaderboard.",
        responses={200: serializers.WadhwaniCollegeLeaderboardSerializer},
    )
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
    @extend_schema(tags=['Leaderboard'], description="Retrieve College Monthly Leaderboard.",
        responses={200: CustomResponseSerializer},
    )
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

class WadhwaniCollegeLeaderboard(APIView):
    @extend_schema(
        tags=['Leaderboard'],
        description="Retrieve Wadhwani College Leaderboard.",
        responses={200: serializers.WadhwaniCollegeLeaderboardSerializer},
    )
    def get(self, request):
        wadhwani_hashtags = [
            "#lp24-interpersonalskills",
            "#lp24-professional",
            "#lp24-obtainanappropriatejob",
            "#ge-speaking-listening",
            "#ge-problemsolving",
            "#cl-entrp-customer",
            "#cl-entrp-mindset",
            "#cl-entrp-intro",
        ]

        wadhwani_task_ids = list(TaskList.objects.filter(
            hashtag__in=wadhwani_hashtags
        ).values_list("id", flat=True))


        college_leaderboard = (
            Organization.objects.filter(
                org_type=OrganizationType.COLLEGE.value,
                user_organization_link_org__user__user_role_link_user__role__title=RoleType.STUDENT.value,
                user_organization_link_org__user__exist_in_guild=True,
                user_organization_link_org__user__karma_activity_log_user__task__in=wadhwani_task_ids,
                user_organization_link_org__user__karma_activity_log_user__appraiser_approved=True,
            )
            .annotate(
                total_karma=Coalesce(
                    Sum(
                        "user_organization_link_org__user__karma_activity_log_user__karma",
                        filter=Q(
                            user_organization_link_org__user__karma_activity_log_user__task__in=wadhwani_task_ids
                        ),
                    ),
                    Value(0),
                ),
                students=Count("user_organization_link_org__user", distinct=True),
                institution=F("title"),
            )
            .values("code", "title", "total_karma", "students")
            .order_by("-total_karma")[:12]
        )

        leaderboard_data = serializers.WadhwaniCollegeLeaderboardSerializer(college_leaderboard, many=True).data
        return CustomResponse(response=leaderboard_data).get_success_response()



class WadhwaniZonalLeaderboard(APIView):
    @extend_schema(
        tags=['Leaderboard'],
        description="Retrieve Wadhwani Zonal Leaderboard.",
        responses={200: serializers.WadhwaniZoneLeaderboardSerializer},
    )
    def get(self, request):
        wadhwani_hashtags = [
            "#lp24-interpersonalskills",
            "#lp24-professional",
            "#lp24-obtainanappropriatejob",
            "#ge-speaking-listening",
            "#ge-problemsolving",
            "#cl-entrp-customer",
            "#cl-entrp-mindset",
            "#cl-entrp-intro",
        ]

        wadhwani_task_ids = list(
            TaskList.objects.filter(hashtag__in=wadhwani_hashtags).values_list("id", flat=True)
        )

        zone_leaderboard = (
            Organization.objects.filter(
                org_type=OrganizationType.COLLEGE.value,
                user_organization_link_org__user__user_role_link_user__role__title=RoleType.STUDENT.value,
                user_organization_link_org__user__exist_in_guild=True,
                user_organization_link_org__user__karma_activity_log_user__task__in=wadhwani_task_ids,
                user_organization_link_org__user__karma_activity_log_user__appraiser_approved=True,
            )
            .annotate(
                zone_name=F("district__zone__name"),
                total_karma=Coalesce(
                    Sum(
                        "user_organization_link_org__user__karma_activity_log_user__karma",
                        filter=Q(
                            user_organization_link_org__user__karma_activity_log_user__task__in=wadhwani_task_ids
                        ),
                    ),
                    Value(0),
                ),
                students=Count("user_organization_link_org__user", distinct=True),
            )
            .values("zone_name")
            .annotate(
                total_karma=F("total_karma"),
                students=F("students"),
            )
            .order_by("-total_karma")
        )

        response_data = serializers.WadhwaniZoneLeaderboardSerializer(zone_leaderboard, many=True).data
        return CustomResponse(response=response_data).get_success_response()