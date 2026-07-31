from django.core.files.storage import FileSystemStorage
from django.db.models import Sum, F, Value, Count, Q, Prefetch, Subquery, OuterRef, IntegerField
from django.db.models.functions import Concat, Coalesce
from rest_framework.views import APIView
from decouple import config as decouple_config
from . import serializers
from db.task import TaskList, InterestGroup
from db.organization import Organization, UserOrganizationLink
from db.user import User, UserRoleLink, UserMentor, MentorScopeGrant, MentorApplication
from db.mentor import MentorshipSession, MentorshipSessionUserLink
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s


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
        responses={200: inline_serializer(
            name='LeaderboardStudentsMonthlyItem',
            fields={
                'muid': s.CharField(),
                'full_name': s.CharField(),
                'total_karma': s.IntegerField(),
                'institution': s.CharField(allow_null=True),
                'profile_pic': s.CharField(allow_null=True),
            },
            many=True,
        )},
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
                "id",
                "muid",
                "full_name",
                "total_karma",
                "institution",
            )
            .order_by("-total_karma")[:20]
        )

        fs = FileSystemStorage()
        result = []
        for student in student_monthly_leaderboard:
            user_id = student.pop("id")
            path = f"user/profile/{user_id}.png"
            student["profile_pic"] = (
                f"{decouple_config('BE_DOMAIN_NAME')}{fs.url(path)}"
                if fs.exists(path)
                else None
            )
            result.append(student)

        return CustomResponse(
            response=result
        ).get_success_response()


class CollegeLeaderboard(APIView):
    @extend_schema(tags=['Leaderboard'], description="Retrieve College Leaderboard.",
        responses={200: inline_serializer(
            name='LeaderboardCollegeItem',
            fields={
                'id': s.CharField(),
                'code': s.CharField(),
                'title': s.CharField(),
                'total_students': s.IntegerField(),
                'total_karma': s.IntegerField(),
            },
            many=True,
        )},
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
            .values("id", "code", "title", "total_students", "total_karma")
            .order_by("-total_karma")[:20]
        )

        return CustomResponse(response=college_leaderboard).get_success_response()


class CollegeMonthlyLeaderboard(APIView):
    @extend_schema(tags=['Leaderboard'], description="Retrieve College Monthly Leaderboard.",
        responses={200: inline_serializer(
            name='LeaderboardCollegeMonthlyItem',
            fields={
                'id': s.CharField(),
                'code': s.CharField(),
                'total_karma': s.IntegerField(),
                'students': s.IntegerField(),
            },
            many=True,
        )},
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
            .values("id", "code", "total_karma", "students")
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


class IGMentorLeaderboard(APIView):
    @extend_schema(
        tags=['Leaderboard'],
        description=(
            "Retrieve the mentor leaderboard for a specific Interest Group. "
            "Mentors are ranked primarily by the number of COMPLETED sessions in that IG, "
            "with total karma as a tiebreaker."
        ),
        responses={200: serializers.IGMentorLeaderboardSerializer(many=True)},
    )
    def get(self, request, ig_id):
        ig = InterestGroup.objects.filter(id=ig_id).first()
        if not ig:
            return CustomResponse(general_message="Interest Group not found").get_failure_response()

        # Sessions completed in this IG by the mentor (linked via MentorshipSessionUserLink)
        completed_sessions_subquery = (
            MentorshipSessionUserLink.objects.filter(
                user_id=OuterRef('user_id'),
                participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
                session__session_type=MentorshipSession.SessionType.IG_SESSION,
                session__entity_id=ig_id,
                session__status=MentorshipSession.Status.COMPLETED,
            )
            .values('user_id')
            .annotate(cnt=Count('id'))
            .values('cnt')
        )

        ig_mentor_user_ids = MentorScopeGrant.objects.filter(
            scope_type=MentorScopeGrant.ScopeType.IG_MENTOR,
            scope_id=str(ig.id),
            is_active=True,
            application__status=MentorApplication.Status.APPROVED,
        ).values_list('application__user_id', flat=True)

        mentor_qs = (
            UserMentor.objects.filter(
                user_id__in=ig_mentor_user_ids,
                is_active=True,
                user__user_ig_link_user__ig=ig,
                user__user_ig_link_user__assignment_type='MENTOR',
                user__user_ig_link_user__is_active=True,
            )
            .select_related('user__wallet_user')
            .annotate(
                total_karma=Coalesce(F('user__wallet_user__karma'), Value(0)),
                completed_sessions=Coalesce(
                    Subquery(completed_sessions_subquery, output_field=IntegerField()),
                    Value(0),
                ),
            )
            .distinct()
            .order_by('-completed_sessions', '-total_karma')
        )

        rankings = {mentor.user_id: idx + 1 for idx, mentor in enumerate(mentor_qs)}
        serialized = serializers.IGMentorLeaderboardSerializer(
            mentor_qs,
            many=True,
            context={'ig': ig, 'rankings': rankings},
        )
        return CustomResponse(response=serialized.data).get_success_response()


class CampusMentorLeaderboard(APIView):
    @extend_schema(
        tags=['Leaderboard'],
        description=(
            "Retrieve the mentor leaderboard for a specific campus. "
            "Mentors are ranked primarily by the number of COMPLETED campus sessions, "
            "with total karma as a tiebreaker."
        ),
        responses={200: serializers.CampusMentorLeaderboardSerializer(many=True)},
    )
    def get(self, request, campus_id):
        campus = Organization.objects.filter(
            id=campus_id, org_type=OrganizationType.COLLEGE.value
        ).first()
        if not campus:
            return CustomResponse(general_message="Campus not found").get_failure_response()

        completed_sessions_subquery = (
            MentorshipSessionUserLink.objects.filter(
                user_id=OuterRef('user_id'),
                participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
                session__session_type=MentorshipSession.SessionType.CAMPUS_SESSION,
                session__entity_id=campus_id,
                session__status=MentorshipSession.Status.COMPLETED,
            )
            .values('user_id')
            .annotate(cnt=Count('id'))
            .values('cnt')
        )

        campus_mentor_user_ids = MentorScopeGrant.objects.filter(
            scope_type=MentorScopeGrant.ScopeType.CAMPUS_MENTOR,
            scope_id=str(campus.id),
            is_active=True,
            application__status=MentorApplication.Status.APPROVED,
        ).values_list('application__user_id', flat=True)

        mentor_qs = (
            UserMentor.objects.filter(
                user_id__in=campus_mentor_user_ids,
                is_active=True,
            )
            .select_related('user__wallet_user')
            .annotate(
                total_karma=Coalesce(F('user__wallet_user__karma'), Value(0)),
                completed_sessions=Coalesce(
                    Subquery(completed_sessions_subquery, output_field=IntegerField()),
                    Value(0),
                ),
            )
            .order_by('-completed_sessions', '-total_karma')
        )

        rankings = {mentor.user_id: idx + 1 for idx, mentor in enumerate(mentor_qs)}
        serialized = serializers.CampusMentorLeaderboardSerializer(
            mentor_qs,
            many=True,
            context={'rankings': rankings, 'campus': campus},
        )
        return CustomResponse(response=serialized.data).get_success_response()


class CompanyMentorLeaderboard(APIView):
    @extend_schema(
        tags=['Leaderboard'],
        description=(
            "Retrieve the mentor leaderboard for a specific company. "
            "Mentors are ranked primarily by the number of COMPLETED company sessions, "
            "with total karma as a tiebreaker."
        ),
        responses={200: serializers.CompanyMentorLeaderboardSerializer(many=True)},
    )
    def get(self, request, company_id):
        from db.company import Company

        company = Company.objects.filter(id=company_id, status="verified").first()
        if not company or not company.org_id:
            return CustomResponse(general_message="Company not found").get_failure_response()

        completed_sessions_subquery = (
            MentorshipSessionUserLink.objects.filter(
                user_id=OuterRef('user_id'),
                participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
                session__session_type=MentorshipSession.SessionType.COMPANY_SESSION,
                session__entity_id=str(company.org_id),
                session__status=MentorshipSession.Status.COMPLETED,
            )
            .values('user_id')
            .annotate(cnt=Count('id'))
            .values('cnt')
        )

        company_mentor_user_ids = MentorScopeGrant.objects.filter(
            scope_type=MentorScopeGrant.ScopeType.COMPANY_MENTOR,
            scope_id=str(company.org_id),
            is_active=True,
            application__status=MentorApplication.Status.APPROVED,
        ).values_list('application__user_id', flat=True)

        mentor_qs = (
            UserMentor.objects.filter(
                user_id__in=company_mentor_user_ids,
                is_active=True,
            )
            .select_related('user__wallet_user')
            .annotate(
                total_karma=Coalesce(F('user__wallet_user__karma'), Value(0)),
                completed_sessions=Coalesce(
                    Subquery(completed_sessions_subquery, output_field=IntegerField()),
                    Value(0),
                ),
            )
            .order_by('-completed_sessions', '-total_karma')
        )

        rankings = {mentor.user_id: idx + 1 for idx, mentor in enumerate(mentor_qs)}
        serialized = serializers.CompanyMentorLeaderboardSerializer(
            mentor_qs,
            many=True,
            context={'rankings': rankings, 'company': company},
        )
        return CustomResponse(response=serialized.data).get_success_response()