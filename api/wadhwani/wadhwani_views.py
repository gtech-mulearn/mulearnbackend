from django.db.models import Sum, F, Value, Count, Q, Prefetch
from django.db.models.functions import Concat, Coalesce
from rest_framework.views import APIView
from . import serializers

from db.organization import Organization, UserOrganizationLink
from db.user import User, UserRoleLink
from db.task import TaskList  # Import your TaskList model
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils

# Make sure this import is present

class WadhwaniStudentsLeaderboard(APIView):
    def get(self, request):
        hashtags = [
            "#lp24-interpersonalskills",
            "#lp24-professional",
            "#lp24-obtainanappropriatejob",
            "#ge-speaking-listening",
            "#ge-problemsolving",
            "#cl-entrp-customer",
            "#cl-entrp-mindset",
            "#cl-entrp-intro",
        ]
        
        task_ids = TaskList.objects.filter(hashtag__in=hashtags).values_list("id", flat=True)

        students_leaderboard = (
            User.objects.filter(
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                user_role_link_user__role__title=RoleType.STUDENT.value,
                exist_in_guild=True,
                wallet_user__karma_source__in=task_ids,
            )
            .distinct()
            .annotate(
                total_karma=Sum(
                    "wallet_user__karma",
                    filter=Q(wallet_user__karma_source__in=task_ids)
                )
            )
            .order_by("-total_karma")[:20]
        )

     
        serialized_students_leaderboard = serializers.StudentLeaderboardSerializer(
            students_leaderboard, many=True
        )

        return CustomResponse(
            response=serialized_students_leaderboard.data
        ).get_success_response()
        
        
class WadhwaniCollegeLeaderboard(APIView):
    def get(self, request):
        hashtags = [
            "#lp24-interpersonalskills",
            "#lp24-professional",
            "#lp24-obtainanappropriatejob",
            "#ge-speaking-listening",
            "#ge-problemsolving",
        ]
        task_ids = TaskList.objects.filter(hashtag__in=hashtags).values_list("id", flat=True)

        college_leaderboard = (
            Organization.objects.filter(
                org_type=OrganizationType.COLLEGE.value,
                user_organization_link_org__user__user_role_link_user__role__title=RoleType.STUDENT.value,
                user_organization_link_org__user__exist_in_guild=True,
                user_organization_link_org__user__wallet_user__karma_source__in=task_ids,
            )
            .distinct()
            .annotate(
                total_students=Count(
                    "user_organization_link_org__user",
                    filter=Q(user_organization_link_org__user__wallet_user__karma_source__in=task_ids),
                    distinct=True
                ),
                total_karma=Sum(
                    "user_organization_link_org__user__wallet_user__karma",
                    filter=Q(user_organization_link_org__user__wallet_user__karma_source__in=task_ids)
                ),
            )
            .values("code", "title", "total_students", "total_karma")
            .order_by("-total_karma")[:12]
        )

        return CustomResponse(response=college_leaderboard).get_success_response()       
        
