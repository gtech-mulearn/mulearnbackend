import uuid

from django.db.models import Sum, Max, Prefetch, F, OuterRef, Subquery, IntegerField, Count, Q

from rest_framework.views import APIView

from .serializers import LaunchpadLeaderBoardSerializer, LaunchpadParticipantsSerializer, LaunchpadUserListSerializer,\
      CollegeDataSerializer, LaunchpadUserSerializer, UserProfileUpdateSerializer, LaunchpadUpdateUserSerializer
from utils.response import CustomResponse
from utils.utils import CommonUtils, ImportCSV
from utils.types import LaunchPadLevels, LaunchPadRoles
from db.user import User, UserRoleLink
from db.organization import UserOrganizationLink, Organization
from db.task import KarmaActivityLog
from db.launchpad import LaunchPadUsers, LaunchPadUserCollegeLink



class Leaderboard(APIView):
    def get(self, request):
        total_karma_subquery = KarmaActivityLog.objects.filter(
            user=OuterRef('id'),
            task__event='launchpad',
            appraiser_approved=True,
        ).values('user').annotate(
            total_karma=Sum('karma')
        ).values('total_karma')
        allowed_org_types = ["College", "School", "Company"]

        intro_task_completed_users = KarmaActivityLog.objects.filter(
            task__event='launchpad',
            appraiser_approved=True,
            task__hashtag='#lp24-introduction',
        ).values('user')
        
        users = User.objects.filter(
            karma_activity_log_user__task__event="launchpad",
            karma_activity_log_user__appraiser_approved=True,
            id__in=intro_task_completed_users
        ).prefetch_related(
            Prefetch(
                "user_organization_link_user",
                queryset=UserOrganizationLink.objects.filter(org__org_type__in=allowed_org_types),
            )
        ).filter(
            Q(user_organization_link_user__id__in=UserOrganizationLink.objects.filter(
                org__org_type__in=allowed_org_types
            ).values("id")) | Q(user_organization_link_user__id__isnull=True)
        ).annotate(
            karma=Subquery(total_karma_subquery, output_field=IntegerField()),
            org=F("user_organization_link_user__org__title"),
            district_name=F("user_organization_link_user__org__district__name"),
            state=F("user_organization_link_user__org__district__zone__state__name"),
            time_=Max("karma_activity_log_user__created_at"),
        ).order_by("-karma", "time_")

        paginated_queryset = CommonUtils.get_paginated_queryset(
            users,
            request,
            ["full_name", "karma", "org", "district_name", "state"]
        )

        serializer = LaunchpadLeaderBoardSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class ListParticipantsAPI(APIView):
    def get(self, request):
        allowed_org_types = ["College", "School", "Company"]
        allowed_levels = LaunchPadLevels.get_all_values()

        intro_task_completed_users = KarmaActivityLog.objects.filter(
            task__event='launchpad',
            appraiser_approved=True,
            task__hashtag='#lp24-introduction',
        ).values('user')

        users = User.objects.filter(
            karma_activity_log_user__task__event="launchpad",
            karma_activity_log_user__appraiser_approved=True,
            id__in=intro_task_completed_users
        ).prefetch_related(
            Prefetch(
                "user_organization_link_user",
                queryset=UserOrganizationLink.objects.filter(org__org_type__in=allowed_org_types),
            ),
            Prefetch(
                "user_role_link_user",
                queryset=UserRoleLink.objects.filter(verified=True, role__title__in=allowed_levels).select_related('role')
            )
        ).filter(
            Q(user_organization_link_user__id__in=UserOrganizationLink.objects.filter(
                org__org_type__in=allowed_org_types
            ).values("id")) | Q(user_organization_link_user__id__isnull=True)
        ).annotate(
            org=F("user_organization_link_user__org__title"),
            district_name=F("user_organization_link_user__org__district__name"),
            state=F("user_organization_link_user__org__district__zone__state__name"),
            level=F("user_role_link_user__role__title"),
            time_=Max("karma_activity_log_user__created_at"),
        ).filter(
            Q(level__in=allowed_levels) | Q(level__isnull=True)
        ).distinct()

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
            sort_fields={"full_name": "full_name", "org": "org", "district_name": "district_name", "state": "state", "level": "level"}
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
            task__event='launchpad',
            appraiser_approved=True,
            task__hashtag='#lp24-introduction',
        ).values('user')

        users = User.objects.filter(
            karma_activity_log_user__task__event="launchpad",
            karma_activity_log_user__appraiser_approved=True,
            id__in=intro_task_completed_users
        ).prefetch_related(
            Prefetch(
                "user_organization_link_user",
                queryset=UserOrganizationLink.objects.filter(org__org_type__in=allowed_org_types),
            ),
            Prefetch(
                "user_role_link_user",
                queryset=UserRoleLink.objects.filter(verified=True,
                                                     role__title__in=allowed_levels).select_related('role')
            )
        ).filter(
            Q(user_organization_link_user__id__in=UserOrganizationLink.objects.filter(
                org__org_type__in=allowed_org_types
            ).values("id")) | Q(user_organization_link_user__id__isnull=True)
        ).annotate(
            org=F("user_organization_link_user__org__title"),
            district_name=F("user_organization_link_user__org__district__name"),
            state=F("user_organization_link_user__org__district__zone__state__name"),
            level=F("user_role_link_user__role__title"),
            time_=Max("karma_activity_log_user__created_at"),
        ).distinct()

        # Count participants at each level
        level_counts = {
            "total_participants": users.values('id').count(),
            "Level_1": users.filter(level=LaunchPadLevels.LEVEL_1.value).count(),
            "Level_2": users.filter(level=LaunchPadLevels.LEVEL_2.value).count(),
            "Level_3": users.filter(level=LaunchPadLevels.LEVEL_3.value).count(),
            "Level_4": users.filter(level=LaunchPadLevels.LEVEL_4.value).count()
        }

        return CustomResponse(response=level_counts).get_success_response()

class CollegeData(APIView):
    def get(self, request):
        allowed_levels = LaunchPadLevels.get_all_values()

        org = Organization.objects.filter(
            org_type="College",
        ).prefetch_related(
            Prefetch(
                "user_organization_link_org",
                queryset=UserOrganizationLink.objects.filter(
                    user__user_role_link_user__role__title__in=allowed_levels
                )
            )
        ).filter(
            user_organization_link_org__user__user_role_link_user__role__title__in=allowed_levels
        ).annotate(
            district_name=F("district__name"),
            state=F("district__zone__state__name"),
            total_users=Count("user_organization_link_org__user"),
            level1 = Count(
                "user_organization_link_org__user", 
                filter=Q(user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_1.value)
            ),
            level2 = Count(
                "user_organization_link_org__user", 
                filter=Q(user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_2.value)
            ),
            level3 = Count(
                "user_organization_link_org__user", 
                filter=Q(user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_3.value)
            ),
            level4 = Count(
                "user_organization_link_org__user", 
                filter=Q(user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_4.value)
            )
        ).order_by("-total_users")
        
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
            sort_fields={"title": "title", "district_name": "district_name", "state": "state"}
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
        auth_mail = data.pop('current_user', None)
        auth_mail = auth_mail[0] if isinstance(auth_mail, list) else auth_mail
        if not (auth_user := LaunchPadUsers.objects.filter(email=auth_mail, role=LaunchPadRoles.ADMIN.value).first()):
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        serializer = LaunchpadUserSerializer(data=data)
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()
        
        colleges = data.get('colleges')
        errors = {}
        error = False
        not_found_colleges = []
        user = serializer.save()
        for college in colleges:
            if not Organization.objects.filter(id=college, org_type="College").exists():
                error = True
                not_found_colleges.append(college)
            elif link := LaunchPadUserCollegeLink.objects.filter(college_id=college).first():
                    link.delete()
            else:
                LaunchPadUserCollegeLink.objects.create(
                    id=uuid.uuid4(),
                    user=user,
                    college_id=college,
                    created_by=auth_user,
                    updated_by=auth_user
                )
        errors[data.get('email')] = {}
        errors[data.get('email')]["not_found_colleges"] = not_found_colleges
        if error:
            return CustomResponse(message=errors).get_failure_response()
        return CustomResponse(general_message="Successfully added user").get_success_response()
    
    def get(self, request):
        auth_mail = request.query_params.get('current_user', None)
        if not LaunchPadUsers.objects.filter(email=auth_mail, role=LaunchPadRoles.ADMIN.value).exists():
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        users = LaunchPadUsers.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(
            users,
            request,
            ["full_name", "phone_number", "email", "role", "district", "zone"]
        )

        serializer = LaunchpadUserListSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )
    
    def put(self, request, email):
        data = request.data
        auth_mail = data.pop('current_user', None)
        auth_mail = auth_mail[0] if isinstance(auth_mail, list) else auth_mail
        if not (auth_user := LaunchPadUsers.objects.filter(email=auth_mail, role=LaunchPadRoles.ADMIN.value).first()):
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        try:
            user = LaunchPadUsers.objects.get(email=email)
        except LaunchPadUsers.DoesNotExist:
            return CustomResponse(general_message="User not found").get_failure_response()
        serializer = LaunchpadUpdateUserSerializer(user, data=data, context={"auth_user": auth_user})
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message="Successfully updated user").get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

class LaunchPadUserPublic(APIView):

    def get(self, request, email):
        try:
            user = LaunchPadUsers.objects.get(email=email)
        except LaunchPadUsers.DoesNotExist:
            return CustomResponse(general_message="User not found").get_failure_response()
        serializer = LaunchpadUserListSerializer(user)
        return CustomResponse(response=serializer.data).get_success_response()
    
    
class UserProfile(APIView):

    def get(self, request):
        auth_mail = request.query_params('current_user', None)
        if not LaunchPadUsers.objects.filter(email=auth_mail).exists():
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        user = LaunchPadUsers.objects.get(email=auth_mail)
        serializer = LaunchpadUserListSerializer(user)
        return CustomResponse(data=serializer.data).get_success_response()
    
    def put(self, request):
        data = request.data
        auth_mail = data.pop('current_user', None)
        auth_mail = auth_mail[0] if isinstance(auth_mail, list) else auth_mail
        if not (user := LaunchPadUsers.objects.filter(email=auth_mail).first()):
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        
        serializer = UserProfileUpdateSerializer(user, data=data)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message="Successfully updated user").get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()
    
    
class UserBasedCollegeData(APIView):

    def get(self, request):
        auth_mail = request.query_params.get('current_user', None)
        if not LaunchPadUsers.objects.filter(email=auth_mail).exists():
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        user = LaunchPadUsers.objects.get(email=auth_mail)
        colleges = LaunchPadUserCollegeLink.objects.filter(user=user)
        college_ids = [college.college_id for college in colleges]

        allowed_levels = LaunchPadLevels.get_all_values()
        
        org = Organization.objects.filter(
            org_type="College",
            id__in=college_ids
        ).prefetch_related(
            Prefetch(
                "user_organization_link_org",
                queryset=UserOrganizationLink.objects.filter(
                    user__user_role_link_user__role__title__in=allowed_levels
                )
            )
        ).filter(
            user_organization_link_org__user__user_role_link_user__role__title__in=allowed_levels
        ).annotate(
            district_name=F("district__name"),
            state=F("district__zone__state__name"),
            total_users=Count("user_organization_link_org__user"),
            level1 = Count(
                "user_organization_link_org__user", 
                filter=Q(user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_1.value)
            ),
            level2 = Count(
                "user_organization_link_org__user", 
                filter=Q(user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_2.value)
            ),
            level3 = Count(
                "user_organization_link_org__user", 
                filter=Q(user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_3.value)
            ),
            level4 = Count(
                "user_organization_link_org__user", 
                filter=Q(user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_4.value)
            )
        ).order_by("-total_users")

        paginated_queryset = CommonUtils.get_paginated_queryset(
            org,
            request,
            ["title", "district_name", "state"]
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
        auth_mail = data.pop('current_user', None)
        auth_mail = auth_mail[0] if isinstance(auth_mail, list) else auth_mail
        if not (auth_user := LaunchPadUsers.objects.filter(email=auth_mail, role=LaunchPadRoles.ADMIN.value).first()):
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        try:
            file_obj = request.FILES['user_data']
        except KeyError:
            return CustomResponse(general_message={'File not found.'}).get_failure_response()
        excel_data = ImportCSV()
        excel_data = excel_data.read_excel_file(file_obj)
        if not excel_data:
            return CustomResponse(general_message={'Empty csv file.'}).get_failure_response()
        errors = {}
        error = False
        
        for data in excel_data[1:]:
            not_found_colleges = []
            data['colleges'] = data['colleges'].split(",") if data.get('colleges') else []
            serializer = LaunchpadUserSerializer(data=data)
            if not serializer.is_valid():
                continue
            user = serializer.save()
            if data.get('colleges') is None:
                continue
            for college in data.get('colleges'):
                if not (org := Organization.objects.filter(title=college, org_type="College").first()):
                    error = True
                    not_found_colleges.append(college)
                elif link := LaunchPadUserCollegeLink.objects.filter(college_id=college).first():
                    link.delete()
                else:
                    LaunchPadUserCollegeLink.objects.create(
                        id=uuid.uuid4(),
                        user=user,
                        college=org,
                        created_by=auth_user,
                        updated_by=auth_user
                    )
            errors[data.get('email')] = {}
            errors[data.get('email')]["not_found_colleges"] = not_found_colleges
        if error:
            return CustomResponse(message=errors).get_failure_response()
        return CustomResponse(general_message="Successfully added users").get_success_response()
