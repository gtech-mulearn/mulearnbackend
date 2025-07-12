import uuid
import jwt
from datetime import timedelta
from decouple import config
from django.db.models import Sum, Max, Prefetch, F, OuterRef, Subquery, IntegerField, Count, Q
from rest_framework.views import APIView
from django.core.files.storage import FileSystemStorage
from decouple import config as decouple_config
from .serializers import (
    LaunchpadLeaderBoardSerializer, LaunchpadParticipantsSerializer, LaunchpadUserListSerializer,
    CollegeDataSerializer, LaunchpadUserSerializer, UserProfileUpdateSerializer,
    LaunchpadUpdateUserSerializer, LaunchPadRankSerializer, TaskCompletedLeaderBoardSerializer,
)
from api.dashboard.profile.profile_serializer import (
    UserProfileSerializer, LinkSocials, UserLevelSerializer, UserLogSerializer,
)
from utils.response import CustomResponse
from utils.utils import CommonUtils, ImportCSV
from utils.types import LaunchPadLevels, LaunchPadRoles
from utils.permission import JWTUtils
from db.user import User, UserRoleLink, Role, Socials
from db.organization import UserOrganizationLink, Organization
from db.task import KarmaActivityLog, Level, TaskList, Wallet
from db.launchpad import LaunchPadUsers, LaunchPadUserCollegeLink, LaunchPad


from rest_framework import status
from db.launchpad import LaunchpadCompanies, LaunchpadRecruiters, LaunchpadJobs
from .serializers import LaunchpadCompaniesSerializer, LaunchpadRecruiterSerializer, LaunchpadJobsSerializer
from django.contrib.auth.hashers import make_password, check_password
from django.db import IntegrityError
from utils.permission import CustomizePermission
from utils.response import CustomResponse
from utils.launchpad_permission import LaunchpadJWTPermission


def get_current_utc_time():
    from django.utils import timezone
    return timezone.now()

def generate_launchpad_jwt(user, user_type):
    access_expiry_time = get_current_utc_time() + timedelta(hours=3)
    access_expiry = access_expiry_time.strftime("%Y-%m-%d %H:%M:%S%z")
    
    access_token = jwt.encode(
        {
            "id": user.id,
            "user_type": user_type,  # "company" or "recruiter"
            "expiry": access_expiry,
            "tokenType": "access",
        },
        config("SECRET_KEY"),
        algorithm="HS256",
    )
    
    refresh_expiry_time = get_current_utc_time() + timedelta(days=7)  # 7 days
    refresh_expiry = refresh_expiry_time.strftime("%Y-%m-%d %H:%M:%S%z")
    
    refresh_token = jwt.encode(
        {
            "id": user.id,
            "user_type": user_type,
            "expiry": refresh_expiry,
            "tokenType": "refresh",
        },
        config("SECRET_KEY"),
        algorithm="HS256",
    )
    return access_token, refresh_token


class RegisterCompanyAPI(APIView):
  def post(self, request):
    required_fields = ['name', 'username']
    for field in required_fields:
      if not request.data.get(field):
        return CustomResponse(
          message={field: [f'{field} is required']},
          general_message="Registration failed"
        ).get_failure_response()

    serializer = LaunchpadCompaniesSerializer(data={
      'id': str(uuid.uuid4()),
      'name': request.data.get('name'),
      'poc_name': request.data.get('poc_name'),
      'poc_role': request.data.get('poc_role'),
      'poc_email': request.data.get('poc_email'),
      'poc_phone': request.data.get('poc_phone') or None,
      'username': request.data.get('username'),
      'password': make_password(request.data.get('password'))
    })

    if serializer.is_valid():
      company = serializer.save()
      return CustomResponse(
        response={
          'id': company.id,
          'name': company.name,
          'username': company.username,
          'poc_name': company.poc_name,
          'poc_email': company.poc_email,
          'created_at': company.created_at
        },
        general_message="Company registered successfully"
      ).get_success_response()

    return CustomResponse(
      message=serializer.errors,
      general_message="Registration failed"
    ).get_failure_response()

class CompanyListAPI(APIView):
  def get(self, request):
    companies = LaunchpadCompanies.objects.all()
    data = [
      {
        'id': company.id,
        'name': company.name
      } for company in companies
    ]
    return CustomResponse(
      response=data,
      general_message="Company list fetched successfully"
    ).get_success_response()

class RegisterRecruiterAPI(APIView):
  permission_classes = [CustomizePermission]
  def post(self, request):
    required_fields = ['company_id', 'name', 'email', 'phone', 'password'
]
    for field in required_fields:
      if not request.data.get(field):
        return CustomResponse(
          message={field: [f'{field} is required']},
          general_message="Signup failed"
        ).get_failure_response()

    serializer = LaunchpadRecruiterSerializer(data={
      'id': str(uuid.uuid4()),
      'company': request.data.get('company_id'),
      'name': request.data.get('name'),
      'email': request.data.get('email'),
      'phone': request.data.get('phone'),
      'password': make_password(request.data.get('password')),
      'role': request.data.get('role')
    })

    if serializer.is_valid():
      try:
        recruiter = serializer.save()
        return CustomResponse(
          response={
            'id': recruiter.id,
            'name': recruiter.name,
            'email': recruiter.email,
            'phone': recruiter.phone,
            'role': recruiter.role,
            'company_id': recruiter.company_id,
            'created_at': recruiter.created_at
          },
          general_message="Recruiter registered successfully"
        ).get_success_response()
      except IntegrityError as e:
        if 'email' in str(e):
          return CustomResponse(
            message={'email': ['A recruiter with this email already exists.']},
            general_message="Signup failed"
          ).get_failure_response()
        else:
          return CustomResponse(
            message={'detail': ['Database error occurred.' + str(e)]},
            general_message="Signup failed"
          ).get_failure_response()

    return CustomResponse(
      message=serializer.errors,
      general_message="Signup failed"
    ).get_failure_response()
  
class AddJobAPI(APIView):
    permission_classes = [LaunchpadJWTPermission]
    
    def post(self, request):
        user = request.launchpad_user
        user_type = request.launchpad_user_type
        
        if user_type != "recruiter":
            return CustomResponse(general_message="Only recruiters can add jobs.").get_failure_response()
        
        required_fields = ['title', 'domain', 'interest_groups']
        for field in required_fields:
            if not request.data.get(field):
                return CustomResponse(
                    message={field: [f'{field} is required']},
                    general_message="Job creation failed"
                ).get_failure_response()
        
        serializer = LaunchpadJobsSerializer(data={
            'id': str(uuid.uuid4()),
            'company': user.company_id,
            'recruiter': user.id,
            'title': request.data.get('title'),
            'skills': request.data.get('skills'),
            'experience': request.data.get('experience'),
            'domain': request.data.get('domain'),
            'interest_groups': request.data.get('interest_groups'),
            'task_description': request.data.get('task_description')
        })

        if serializer.is_valid():
            try:
                job = serializer.save()
                response_data = {
                    'id': job.id,
                    'company_id': job.company_id,
                    'recruiter_id': job.recruiter_id,
                    'title': job.title,
                    'skills': job.skills or None,
                    'experience': job.experience or None,
                    'domain': job.domain,
                    'interest_groups': job.interest_groups,
                    'task_description': job.task_description or None,
                    'created_at': job.created_at
                }
                return CustomResponse(
                    response=response_data,
                    general_message="Job created successfully"
                ).get_success_response()
            except IntegrityError as e:
                return CustomResponse(
                    message={'detail': ['Database error occurred.' + str(e)]},
                    general_message="Job creation failed"
                ).get_failure_response()

        return CustomResponse(
            message=serializer.errors,
            general_message="Job creation failed"
        ).get_failure_response()
  
class LoginCompanyAPI(APIView):
    def post(self, request):
        data = request.data
        usernameOrEmail = data.get("username") or data.get("email")
        password = data.get("password")
        if not usernameOrEmail or not password:
            return CustomResponse(general_message="Username/email and password are required.").get_failure_response()
        
        company = None
        try:
            company = LaunchpadCompanies.objects.get(username=usernameOrEmail)
        except LaunchpadCompanies.DoesNotExist:
            try:
                company = LaunchpadCompanies.objects.get(poc_email=usernameOrEmail)
            except LaunchpadCompanies.DoesNotExist:
                return CustomResponse(general_message="Invalid credentials.").get_failure_response()
        
        if not check_password(password, company.password):
            return CustomResponse(general_message="Invalid credentials.").get_failure_response()
        
        access_token, refresh_token = generate_launchpad_jwt(company, "company")
        
        return CustomResponse(response={
            'id': company.id,
            'name': company.name,
            'username': company.username,
            'poc_name': company.poc_name,
            'poc_email': company.poc_email,
            'created_at': company.created_at,
            'accessToken': access_token,
            'refreshToken': refresh_token
        }).get_success_response()

class LoginRecruiterAPI(APIView):
    def post(self, request):
        data = request.data
        emailOrPhone = data.get('email') or data.get('phone')
        password = data.get("password")
        if not emailOrPhone or not password:
            return CustomResponse(general_message="Email/phone and password are required.").get_failure_response()
        
        recruiter = None
        try:
            recruiter = LaunchpadRecruiters.objects.get(email=emailOrPhone)
        except LaunchpadRecruiters.DoesNotExist:
            try:
                recruiter = LaunchpadRecruiters.objects.get(phone=emailOrPhone)
            except LaunchpadRecruiters.DoesNotExist:
                return CustomResponse(general_message="Invalid credentials.").get_failure_response()
        
        if not check_password(password, recruiter.password):
            return CustomResponse(general_message="Invalid credentials.").get_failure_response()
        
        access_token, refresh_token = generate_launchpad_jwt(recruiter, "recruiter")
        
        return CustomResponse(response={
            'id': recruiter.id,
            'name': recruiter.name,
            'email': recruiter.email,
            'phone': recruiter.phone,
            'role': recruiter.role,
            'company_id': recruiter.company_id,
            'created_at': recruiter.created_at,
            'accessToken': access_token,
            'refreshToken': refresh_token
        }).get_success_response()

class GetCompanyInfoAPI(APIView):
    def post(self, request):
        company_id = request.data.get('company_id')
        if not company_id:
            return CustomResponse(general_message="Company ID is required.").get_failure_response()
        
        try:
            company = LaunchpadCompanies.objects.get(id=company_id)
            return CustomResponse(response={
                'id': company.id,
                'name': company.name,
                'username': company.username,
                'poc_name': company.poc_name,
                'poc_role': company.poc_role,
                'poc_email': company.poc_email,
                'poc_phone': company.poc_phone,
                'created_at': company.created_at,
                'updated_at': company.updated_at,
                'recruiters': [
                    {
                        'id': recruiter.id,
                        'name': recruiter.name,
                        'email': recruiter.email,
                        'phone': recruiter.phone,
                        'role': recruiter.role,
                        'created_at': recruiter.created_at,
                        'updated_at': recruiter.updated_at
                    }
                    for recruiter in LaunchpadRecruiters.objects.filter(company=company)
                ]

            }).get_success_response()
        except LaunchpadCompanies.DoesNotExist:
            return CustomResponse(general_message="Company not found.").get_failure_response()

class GetRecruiterInfoAPI(APIView):
    def post(self, request):
        recruiter_id = request.data.get('recruiter_id')
        if not recruiter_id:
            return CustomResponse(general_message="Recruiter ID is required.").get_failure_response()
        
        try:
            recruiter = LaunchpadRecruiters.objects.select_related('company').get(id=recruiter_id)
            return CustomResponse(response={
                'id': recruiter.id,
                'name': recruiter.name,
                'email': recruiter.email,
                'phone': recruiter.phone,
                'role': recruiter.role,
                'company_id': recruiter.company_id,
                'company_name': recruiter.company.name if recruiter.company else None,
                'created_at': recruiter.created_at,
                'updated_at': recruiter.updated_at
            }).get_success_response()
        except LaunchpadRecruiters.DoesNotExist:
            return CustomResponse(general_message="Recruiter not found.").get_failure_response()


class RefreshTokenAPI(APIView):
    def post(self, request):
        refresh_token = request.data.get("refreshToken")
        if not refresh_token:
            return CustomResponse(general_message="Refresh token is required.").get_failure_response()
        
        try:
            payload = jwt.decode(
                refresh_token,
                config("SECRET_KEY"),
                algorithms=["HS256"],
                verify=True,
            )
        except jwt.ExpiredSignatureError:
            return CustomResponse(general_message="Refresh token has expired.").get_failure_response()
        except jwt.InvalidTokenError:
            return CustomResponse(general_message="Invalid refresh token.").get_failure_response()
        
        user_id = payload.get("id")
        user_type = payload.get("user_type")
        token_type = payload.get("tokenType")
        
        if token_type != "refresh":
            return CustomResponse(general_message="Invalid token type.").get_failure_response()

        user = None
        if user_type == "company":
            try:
                user = LaunchpadCompanies.objects.get(id=user_id)
            except LaunchpadCompanies.DoesNotExist:
                return CustomResponse(general_message="Company not found.").get_failure_response()
        elif user_type == "recruiter":
            try:
                user = LaunchpadRecruiters.objects.get(id=user_id)
            except LaunchpadRecruiters.DoesNotExist:
                return CustomResponse(general_message="Recruiter not found.").get_failure_response()
        else:
            return CustomResponse(general_message="Invalid user type.").get_failure_response()
        
        # Generate new tokens
        access_token, new_refresh_token = generate_launchpad_jwt(user, user_type)
        
        return CustomResponse(response={
            "accessToken": access_token,
            "refreshToken": new_refresh_token
        }).get_success_response()

class CompanyVerifyAPI(APIView):
    def post(self, request):
        company_id = request.data.get('id')

        if not company_id:
            return CustomResponse(general_message="Company ID is required.").get_failure_response()

        try:
            company = LaunchpadCompanies.objects.get(id=company_id)
            company.is_verified = True
            company.save()

            return CustomResponse(response={
                "company_name": company.name,
                "message": f"Company '{company.name}' verified successfully."
            }).get_success_response()

        except LaunchpadCompanies.DoesNotExist:
            return CustomResponse(general_message="Company not found.").get_failure_response()


#<--------------------------------------------------- old launchpad ------------------------------------------------->
class Leaderboard(APIView):
    def get(self, request):
        total_karma_subquery = (
            KarmaActivityLog.objects.filter(
                user=OuterRef("id"),
                task__event="launchpad",
                appraiser_approved=True,
            )
            .values("user")
            .annotate(total_karma=Sum("karma"))
            .values("total_karma")
        )
        allowed_org_types = ["College", "School", "Company"]

        intro_task_completed_users = KarmaActivityLog.objects.filter(
            task__event="launchpad",
            appraiser_approved=True,
            task__hashtag="#lp24-introduction",
        ).values("user")

        latest_org_link = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__title")[:1]
        )

        latest_district = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__name")[:1]
        )

        latest_state = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__zone__state__name")[:1]
        )

        users = (
            User.objects.filter(
                karma_activity_log_user__task__event="launchpad",
                karma_activity_log_user__appraiser_approved=True,
                id__in=intro_task_completed_users,
            )
            .annotate(
                karma=Subquery(total_karma_subquery, output_field=IntegerField()),
                org=Subquery(latest_org_link),
                district_name=Subquery(latest_district),
                state=Subquery(latest_state),
                time_=Max("karma_activity_log_user__created_at"),
            )
            .order_by("-karma", "time_")
        )

        rank_list = list(users)
        for index, user in enumerate(rank_list):
            user.rank = index + 1

        paginated_queryset = CommonUtils.get_paginated_queryset(
            users, request, ["full_name", "karma", "org", "district_name", "state"]
        )

        final_users = paginated_queryset.get("queryset")
        if request.query_params.get("search"):
            final_users = list(final_users)
            for user in final_users:
                user.rank = next(
                    rank_user.rank
                    for rank_user in rank_list
                    if rank_user.muid == user.muid
                )

        serializer = LaunchpadLeaderBoardSerializer(final_users, many=True)

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class TaskCompletedLeaderboard(APIView):
    def get(self, request):

        launchpad_tasks = TaskList.objects.filter(event="launchpad").values("id")

        completed_tasks_counts = (
            KarmaActivityLog.objects.filter(
                task__event="launchpad",
                appraiser_approved=True,
            )
            .values("user")
            .annotate(completed_tasks=Count("task", distinct=True))
            .filter(completed_tasks=launchpad_tasks.count())
        )

        allowed_org_types = ["College", "School", "Company"]

        completed_users = completed_tasks_counts.values("user")

        latest_org_link = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__title")[:1]
        )

        latest_district = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__name")[:1]
        )

        latest_state = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__zone__state__name")[:1]
        )

        wallet_subquery = Wallet.objects.filter(user=OuterRef("id")).values("karma")[:1]

        users = (
            User.objects.filter(
                karma_activity_log_user__task__event="launchpad",
                karma_activity_log_user__appraiser_approved=True,
                id__in=completed_users,
            )
            .annotate(
                karma=Subquery(wallet_subquery, output_field=IntegerField()),
                org=Subquery(latest_org_link),
                district_name=Subquery(latest_district),
                state=Subquery(latest_state),
                time_=Max("karma_activity_log_user__created_at"),
            )
            .order_by("-karma", "time_")
        )

        rank_list = list(users)
        for index, user in enumerate(rank_list):
            user.rank = index + 1

        paginated_queryset = CommonUtils.get_paginated_queryset(
            users, request, ["muid", "full_name", "org"]
        )

        final_users = paginated_queryset.get("queryset")
        if request.query_params.get("search"):
            final_users = list(final_users)
            for user in final_users:
                user.rank = next(
                    rank_user.rank
                    for rank_user in rank_list
                    if rank_user.muid == user.muid
                )

        serializer = TaskCompletedLeaderBoardSerializer(final_users, many=True)
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class ListParticipantsAPI(APIView):
    def get(self, request):
        allowed_org_types = ["College", "School", "Company"]
        allowed_levels = LaunchPadLevels.get_all_values()

        intro_task_completed_users = KarmaActivityLog.objects.filter(
            task__event="launchpad",
            appraiser_approved=True,
            task__hashtag="#lp24-introduction",
        ).values("user")

        latest_org_link = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__title")[:1]
        )

        latest_district = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__name")[:1]
        )

        latest_state = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__zone__state__name")[:1]
        )

        users = (
            User.objects.filter(
                karma_activity_log_user__task__event="launchpad",
                karma_activity_log_user__appraiser_approved=True,
                id__in=intro_task_completed_users,
            )
            .prefetch_related(
                Prefetch(
                    "user_role_link_user",
                    queryset=UserRoleLink.objects.filter(
                        verified=True, role__title__in=allowed_levels
                    ).select_related("role"),
                )
            )
            .annotate(
                org=Subquery(latest_org_link),
                district_name=Subquery(latest_district),
                state=Subquery(latest_state),
                level=F("user_role_link_user__role__title"),
                time_=Max("karma_activity_log_user__created_at"),
            )
            .filter(Q(level__in=allowed_levels) | Q(level__isnull=True))
            .distinct()
        )

        if district := request.query_params.get("district"):
            users = users.filter(district_name=district)
        if org := request.query_params.get("org"):
            users = users.filter(org=org)
        if level := request.query_params.get("level"):
            users = users.filter(level=level)
        if state := request.query_params.get("state"):
            users = users.filter(state=state)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            users,
            request,
            ["full_name", "level", "org", "district_name", "state"],
            sort_fields={
                "full_name": "full_name",
                "org": "org",
                "district_name": "district_name",
                "state": "state",
                "level": "level",
            },
        )

        serializer = LaunchpadParticipantsSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class LaunchpadDetailsCount(APIView):
    def get(self, request):
        allowed_org_types = ["College", "School", "Company"]
        allowed_levels = LaunchPadLevels.get_all_values()

        intro_task_completed_users = KarmaActivityLog.objects.filter(
            task__event="launchpad",
            appraiser_approved=True,
            task__hashtag="#lp24-introduction",
        ).values("user")

        latest_org_link = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__title")[:1]
        )

        latest_district = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__name")[:1]
        )

        latest_state = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__zone__state__name")[:1]
        )

        users = (
            User.objects.filter(
                karma_activity_log_user__task__event="launchpad",
                karma_activity_log_user__appraiser_approved=True,
                id__in=intro_task_completed_users,
            )
            .prefetch_related(
                Prefetch(
                    "user_role_link_user",
                    queryset=UserRoleLink.objects.filter(
                        verified=True, role__title__in=allowed_levels
                    ).select_related("role"),
                )
            )
            .annotate(
                org=Subquery(latest_org_link),
                district_name=Subquery(latest_district),
                state=Subquery(latest_state),
                level=F("user_role_link_user__role__title"),
                time_=Max("karma_activity_log_user__created_at"),
            )
            .distinct()
        )

        # Count participants at each level
        level_counts = {
            "total_participants": users.values("id").count(),
            "Level_1": users.filter(level=LaunchPadLevels.LEVEL_1.value).count(),
            "Level_2": users.filter(level=LaunchPadLevels.LEVEL_2.value).count(),
            "Level_3": users.filter(level=LaunchPadLevels.LEVEL_3.value).count(),
            "Level_4": users.filter(level=LaunchPadLevels.LEVEL_4.value).count(),
        }

        return CustomResponse(response=level_counts).get_success_response()


class CollegeData(APIView):
    def get(self, request):
        allowed_levels = LaunchPadLevels.get_all_values()

        org = (
            Organization.objects.filter(
                org_type="College",
            )
            .prefetch_related(
                Prefetch(
                    "user_organization_link_org",
                    queryset=UserOrganizationLink.objects.filter(
                        user__user_role_link_user__role__title__in=allowed_levels
                    ),
                )
            )
            .filter(
                user_organization_link_org__user__user_role_link_user__role__title__in=allowed_levels
            )
            .annotate(
                district_name=F("district__name"),
                state=F("district__zone__state__name"),
                total_users=Count("user_organization_link_org__user"),
                level1=Count(
                    "user_organization_link_org__user",
                    filter=Q(
                        user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_1.value
                    ),
                ),
                level2=Count(
                    "user_organization_link_org__user",
                    filter=Q(
                        user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_2.value
                    ),
                ),
                level3=Count(
                    "user_organization_link_org__user",
                    filter=Q(
                        user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_3.value
                    ),
                ),
                level4=Count(
                    "user_organization_link_org__user",
                    filter=Q(
                        user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_4.value
                    ),
                ),
            )
            .order_by("-total_users")
        )

        if district := request.query_params.get("district"):
            org = org.filter(district_name=district)
        if title := request.query_params.get("title"):
            org = org.filter(title=title)
        if state := request.query_params.get("state"):
            org = org.filter(state=state)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            org,
            request,
            ["title", "district_name", "state"],
            sort_fields={
                "title": "title",
                "district_name": "district_name",
                "state": "state",
            },
        )

        serializer = CollegeDataSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class LaunchPadUser(APIView):

    def post(self, request):
        data = request.data
        auth_mail = data.pop("current_user", None)
        auth_mail = auth_mail[0] if isinstance(auth_mail, list) else auth_mail
        if not (
            auth_user := LaunchPadUsers.objects.filter(
                email=auth_mail, role=LaunchPadRoles.ADMIN.value
            ).first()
        ):
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        serializer = LaunchpadUserSerializer(data=data)
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        colleges = data.get("colleges")
        errors = {}
        error = False
        not_found_colleges = []
        user = serializer.save()
        for college in colleges:
            if not Organization.objects.filter(id=college, org_type="College").exists():
                error = True
                not_found_colleges.append(college)
            elif link := LaunchPadUserCollegeLink.objects.filter(
                college_id=college
            ).first():
                link.delete()
            else:
                LaunchPadUserCollegeLink.objects.create(
                    id=uuid.uuid4(),
                    user=user,
                    college_id=college,
                    created_by=auth_user,
                    updated_by=auth_user,
                )
        errors[data.get("email")] = {}
        errors[data.get("email")]["not_found_colleges"] = not_found_colleges
        if error:
            return CustomResponse(message=errors).get_failure_response()
        return CustomResponse(
            general_message="Successfully added user"
        ).get_success_response()

    def get(self, request):
        auth_mail = request.query_params.get("current_user", None)
        if not LaunchPadUsers.objects.filter(
            email=auth_mail, role=LaunchPadRoles.ADMIN.value
        ).exists():
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        users = LaunchPadUsers.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(
            users,
            request,
            ["full_name", "phone_number", "email", "role", "district", "zone"],
        )

        serializer = LaunchpadUserListSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )

    def put(self, request, email):
        data = request.data
        auth_mail = data.pop("current_user", None)
        auth_mail = auth_mail[0] if isinstance(auth_mail, list) else auth_mail
        if not (
            auth_user := LaunchPadUsers.objects.filter(
                email=auth_mail, role=LaunchPadRoles.ADMIN.value
            ).first()
        ):
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        try:
            user = LaunchPadUsers.objects.get(email=email)
        except LaunchPadUsers.DoesNotExist:
            return CustomResponse(
                general_message="User not found"
            ).get_failure_response()
        serializer = LaunchpadUpdateUserSerializer(
            user, data=data, context={"auth_user": auth_user}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Successfully updated user"
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class LaunchPadUserPublic(APIView):

    def get(self, request, email):
        try:
            user = LaunchPadUsers.objects.get(email=email)
        except LaunchPadUsers.DoesNotExist:
            return CustomResponse(
                general_message="User not found"
            ).get_failure_response()
        serializer = LaunchpadUserListSerializer(user)
        return CustomResponse(response=serializer.data).get_success_response()


class UserProfile(APIView):

    def get(self, request):
        auth_mail = request.query_params.get("current_user", None)
        if not LaunchPadUsers.objects.filter(email=auth_mail).exists():
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        user = LaunchPadUsers.objects.get(email=auth_mail)
        serializer = LaunchpadUserListSerializer(user)
        return CustomResponse(response=serializer.data).get_success_response()

    def put(self, request):
        data = request.data
        auth_mail = data.pop("current_user", None)
        auth_mail = auth_mail[0] if isinstance(auth_mail, list) else auth_mail
        if not (user := LaunchPadUsers.objects.filter(email=auth_mail).first()):
            return CustomResponse(general_message="Unauthorized").get_failure_response()

        serializer = UserProfileUpdateSerializer(user, data=data)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Successfully updated user"
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class UserBasedCollegeData(APIView):

    def get(self, request):
        auth_mail = request.query_params.get("current_user", None)
        if not LaunchPadUsers.objects.filter(email=auth_mail).exists():
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        user = LaunchPadUsers.objects.get(email=auth_mail)
        colleges = LaunchPadUserCollegeLink.objects.filter(user=user)
        college_ids = [college.college_id for college in colleges]

        allowed_levels = LaunchPadLevels.get_all_values()

        org = (
            Organization.objects.filter(org_type="College", id__in=college_ids)
            .prefetch_related(
                Prefetch(
                    "user_organization_link_org",
                    queryset=UserOrganizationLink.objects.filter(
                        user__user_role_link_user__role__title__in=allowed_levels
                    ),
                )
            )
            .filter(
                user_organization_link_org__user__user_role_link_user__role__title__in=allowed_levels
            )
            .annotate(
                district_name=F("district__name"),
                state=F("district__zone__state__name"),
                total_users=Count("user_organization_link_org__user"),
                level1=Count(
                    "user_organization_link_org__user",
                    filter=Q(
                        user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_1.value
                    ),
                ),
                level2=Count(
                    "user_organization_link_org__user",
                    filter=Q(
                        user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_2.value
                    ),
                ),
                level3=Count(
                    "user_organization_link_org__user",
                    filter=Q(
                        user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_3.value
                    ),
                ),
                level4=Count(
                    "user_organization_link_org__user",
                    filter=Q(
                        user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_4.value
                    ),
                ),
            )
            .order_by("-total_users")
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            org, request, ["title", "district_name", "state"]
        )

        serializer = CollegeDataSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class BulkLaunchpadUser(APIView):

    def post(self, request):
        data = request.data
        auth_mail = data.pop("current_user", None)
        auth_mail = auth_mail[0] if isinstance(auth_mail, list) else auth_mail
        if not (
            auth_user := LaunchPadUsers.objects.filter(
                email=auth_mail, role=LaunchPadRoles.ADMIN.value
            ).first()
        ):
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        try:
            file_obj = request.FILES["user_data"]
        except KeyError:
            return CustomResponse(
                general_message={"File not found."}
            ).get_failure_response()
        excel_data = ImportCSV()
        excel_data = excel_data.read_excel_file(file_obj)
        if not excel_data:
            return CustomResponse(
                general_message={"Empty csv file."}
            ).get_failure_response()
        errors = {}
        error = False

        for data in excel_data[1:]:
            not_found_colleges = []
            data["colleges"] = (
                data["colleges"].split(",") if data.get("colleges") else []
            )
            serializer = LaunchpadUserSerializer(data=data)
            if not serializer.is_valid():
                continue
            user = serializer.save()
            if data.get("colleges") is None:
                continue
            for college in data.get("colleges"):
                if not (
                    org := Organization.objects.filter(
                        title=college, org_type="College"
                    ).first()
                ):
                    error = True
                    not_found_colleges.append(college)
                elif link := LaunchPadUserCollegeLink.objects.filter(
                    college_id=college
                ).first():
                    link.delete()
                else:
                    LaunchPadUserCollegeLink.objects.create(
                        id=uuid.uuid4(),
                        user=user,
                        college=org,
                        created_by=auth_user,
                        updated_by=auth_user,
                    )
            errors[data.get("email")] = {}
            errors[data.get("email")]["not_found_colleges"] = not_found_colleges
        if error:
            return CustomResponse(message=errors).get_failure_response()
        return CustomResponse(
            general_message="Successfully added users"
        ).get_success_response()


class LaunchPadListAdmin(APIView):

    def get(self, request):
        auth_mail = request.query_params.get("current_user", None)
        auth_mail = auth_mail[0] if isinstance(auth_mail, list) else auth_mail
        if not (
            auth_user := LaunchPadUsers.objects.filter(
                email=auth_mail, role=LaunchPadRoles.ADMIN.value
            ).first()
        ):
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        total_karma_subquery = (
            KarmaActivityLog.objects.filter(
                user=OuterRef("id"),
                task__event="launchpad",
                appraiser_approved=True,
            )
            .values("user")
            .annotate(total_karma=Sum("karma"))
            .values("total_karma")
        )
        allowed_org_types = ["College", "School", "Company"]

        intro_task_completed_users = KarmaActivityLog.objects.filter(
            task__event="launchpad",
            appraiser_approved=True,
            task__hashtag="#lp24-introduction",
        ).values("user")

        latest_org_link = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__title")[:1]
        )

        latest_district = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__name")[:1]
        )

        latest_state = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__zone__state__name")[:1]
        )

        users = (
            User.objects.filter(
                karma_activity_log_user__task__event="launchpad",
                karma_activity_log_user__appraiser_approved=True,
                id__in=intro_task_completed_users,
            )
            .annotate(
                karma=Subquery(total_karma_subquery, output_field=IntegerField()),
                org=Subquery(latest_org_link),
                district_name=Subquery(latest_district),
                state=Subquery(latest_state),
                time_=Max("karma_activity_log_user__created_at"),
            )
            .order_by("-karma", "time_")
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            users, request, ["full_name", "karma", "org", "district_name", "state"]
        )

        serializer = LaunchpadLeaderBoardSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class BaseAPI(APIView):
    def get_authenticated_user(self, request, launchpad_id):
        auth_mail = request.query_params.get("current_user", None)
        auth_mail = auth_mail[0] if isinstance(auth_mail, list) else auth_mail
        if launchpad_id is None:
            return (
                None,
                CustomResponse(
                    general_message="No launchpad id provided"
                ).get_failure_response(),
            )
        if not (
            auth_user := LaunchPadUsers.objects.filter(
                email=auth_mail, role=LaunchPadRoles.ADMIN.value
            ).first()
        ):
            return (
                None,
                CustomResponse(general_message="Unauthorized").get_failure_response(),
            )
        try:
            user = LaunchPad.objects.get(launchpad_id=launchpad_id).user
        except LaunchPad.DoesNotExist:
            return (
                None,
                CustomResponse(
                    general_message="Invalid Launchpad ID"
                ).get_failure_response(),
            )
        return user, None


class UserProfileAPI(BaseAPI):
    def get(self, request, launchpad_id=None):
        user, response = self.get_authenticated_user(request, launchpad_id)
        if response:
            return response
        serializer = UserProfileSerializer(user, many=False)
        launchpad_karma = (
            KarmaActivityLog.objects.filter(
                user=user,
                task__event="launchpad",
                appraiser_approved=True,
            ).aggregate(total_karma=Sum("karma"))["total_karma"]
            or 0
        )
        rank_serializer = LaunchPadRankSerializer(user)
        launchpad_rank = rank_serializer.data["launchpad_rank"]

        data = serializer.data
        data["launchpad_karma"] = launchpad_karma
        data["launchpad_rank"] = launchpad_rank
        return CustomResponse(response=data).get_success_response()


class GetSocialsAPI(BaseAPI):
    def get(self, request, launchpad_id=None):
        user, response = self.get_authenticated_user(request, launchpad_id)
        if response:
            return response
        social_instance = Socials.objects.filter(user_id=user.id).first()
        serializer = LinkSocials(instance=social_instance)
        return CustomResponse(response=serializer.data).get_success_response()


class UserLevelsAPI(BaseAPI):
    def get(self, request, launchpad_id=None):
        user, response = self.get_authenticated_user(request, launchpad_id)
        if response:
            return response
        user_levels_link_query = Level.objects.all().order_by("level_order")
        serializer = UserLevelSerializer(
            user_levels_link_query, many=True, context={"user_id": user.id}
        )
        return CustomResponse(response=serializer.data).get_success_response()


class UserLogAPI(BaseAPI):
    def get(self, request, launchpad_id=None):
        launchpad_log = request.query_params.get("launchpad_log", False)
        user, response = self.get_authenticated_user(request, launchpad_id)
        if response:
            return response

        query = Q(user=user.id, appraiser_approved=True)
        if launchpad_log:
            query &= Q(task__event="launchpad")
        karma_activity_log = KarmaActivityLog.objects.filter(query).order_by(
            "-created_at"
        )
        if not karma_activity_log.exists():
            return CustomResponse(
                general_message="No karma details available for user"
            ).get_success_response()

        serializer = UserLogSerializer(karma_activity_log, many=True)
        return CustomResponse(response=serializer.data).get_success_response()


class IGLeaderboardView(APIView):
    def get(self, request):
        category = request.query_params.get("category")
        # ig_id = request.query_params.get("ig_id")

        if category is None:
            return CustomResponse(
                general_message="No category provided"
            ).get_failure_response()

        # if ig_id is None:
        #     return CustomResponse(
        #         general_message="No IG ID provided"
        #     ).get_failure_response()

        logs = (
            KarmaActivityLog.objects.select_related("user", "task", "task__ig")
            .prefetch_related("user__wallet_user")
            .filter(task__ig__category=category, appraiser_approved=True)
            .values("user_id", "task__ig__category")
            .annotate(
                category_karma=Sum("karma"),
            )
            .order_by("-category_karma")
            .values(
                "user_id",
                "user__full_name",
                "user__email",
                "user__muid",
                # "user__profile_pic",
                "category_karma",
                "user__wallet_user__karma",
            )
        )
        fs = FileSystemStorage()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            logs,
            request,
            search_fields=[
                "user__full_name",
                "user__email",
                "user__muid",
            ],
            sort_fields={
                "category_karma": "category_karma",
                "total_karma": "user__wallet_user__karma",
            },
        )

        ig_data = {}
        for entry in (
            KarmaActivityLog.objects.select_related("task__ig")
            .filter(
                appraiser_approved=True,
                task__ig__category=category,
                user_id__in=[
                    row.get("user_id") for row in paginated_queryset.get("queryset")
                ],
            )
            .values("task__ig_id", "user_id")
            .annotate(ig_karma=Sum("karma"))
            .values("user_id", "ig_karma", "task__ig__name", "task__ig_id")
        ):
            if not ig_data.get(entry.get("user_id")):
                ig_data[entry.get("user_id")] = []
            ig_data[entry.get("user_id")].append(
                {
                    "ig_id": entry.get("task__ig_id"),
                    "ig_karma": entry.get("ig_karma"),
                    "ig_name": entry.get("task__ig__name"),
                }
            )

        data = [
            {
                "full_name": row.get("user__full_name"),
                "email": row.get("user__email"),
                "muid": row.get("user__muid"),
                "profile_pic": (
                    f"{decouple_config('BE_DOMAIN_NAME')}{fs.url('user/profile/{}.png'.format('user_id'))}"
                    if fs.exists("user/profile/{}.png".format("user_id"))
                    else None
                ),
                "category_karma": row.get("category_karma"),
                "total_karma": row.get("user__wallet_user__karma"),
                "ig_data": ig_data.get(row.get("user_id")),
            }
            for row in paginated_queryset.get("queryset")
        ]
        return CustomResponse().paginated_response(
            data=data, pagination=paginated_queryset.get("pagination")
        )
