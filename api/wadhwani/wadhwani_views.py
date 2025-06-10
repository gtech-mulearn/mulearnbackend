from django.db.models import Sum, Count, Q, Value, F
from django.db.models.functions import Coalesce
from rest_framework.views import APIView

from db.organization import Organization
from db.task import TaskList
from db.user import User
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from .serializers import WadhwaniCollegeLeaderboardSerializer, WadhwaniZoneLeaderboardSerializer

class WadhwaniCollegeLeaderboard(APIView):
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

        leaderboard_data = WadhwaniCollegeLeaderboardSerializer(college_leaderboard, many=True).data
        return CustomResponse(response=leaderboard_data).get_success_response()



class WadhwaniZonalLeaderboard(APIView):
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

        response_data = WadhwaniZoneLeaderboardSerializer(zone_leaderboard, many=True).data
        return CustomResponse(response=response_data).get_success_response()

