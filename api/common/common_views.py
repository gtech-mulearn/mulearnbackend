import json

import requests
from django.db import models
from django.db.models import Case, When, Value, CharField, Count, Q, F, Sum
from django.db.models import Subquery, OuterRef
from django.db.models.functions import Coalesce
from rest_framework.views import APIView

from db.learning_circle import LearningCircle
from db.learning_circle import UserCircleLink
from db.organization import Organization,Department,District,State,Country
from db.task import InterestGroup, KarmaActivityLog, Level, TaskList, UserIgLink
from db.user import User, UserRoleLink
from utils.response import CustomResponse
from utils.types import IntegrationType, OrganizationType, RoleType
from utils.utils import CommonUtils
from .serializer import StudentInfoSerializer, CollegeInfoSerializer, LearningCircleEnrollmentSerializer, \
    UserLeaderboardSerializer,OrgSerializer,DistrictSerializer,StateSerializer,CountrySerializer, LcDetailsSerializer, \
    LcListSerializer
from api.dashboard.ig.dash_ig_serializer import InterestGroupSerializer
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiResponse
from rest_framework import serializers as s

class LcDetailsAPI(APIView):
    @extend_schema(
        tags=['Common'],
        description="Retrieve Lc Details.",
        responses={200: inline_serializer("CommonLcDetailsResponse", fields={
            "hasError": s.BooleanField(default=False),
            "statusCode": s.IntegerField(default=200),
            "message": s.DictField(child=s.CharField(), default={}),
            "response": inline_serializer("CommonLcDetailsData", fields={
                "name": s.CharField(),
                "circle_code": s.CharField(),
                "note": s.CharField(allow_null=True),
                "day": s.CharField(allow_null=True),
                "college": s.CharField(allow_null=True),
                "members": s.ListField(child=s.DictField()),
                "rank": s.IntegerField(allow_null=True),
                "total_karma": s.IntegerField(),
                "ig_id": s.CharField(),
                "ig_name": s.CharField(),
                "ig_code": s.CharField(),
            }),
        })},
    )
    def get(self, request, circle_id):
        learning_circle = LearningCircle.objects.filter(id=circle_id).first()

        serializer = LcDetailsSerializer(
            learning_circle,
            many=False,
            context={"circle_id": circle_id},
        )

        return CustomResponse(response=serializer.data).get_success_response()

class LcListAPI(APIView):
    @extend_schema(
        tags=['Common'],
        description="Retrieve Lc List.",
        responses={200: inline_serializer("CommonLcListResponse", fields={
            "hasError": s.BooleanField(default=False),
            "statusCode": s.IntegerField(default=200),
            "message": s.DictField(child=s.CharField(), default={}),
            "response": s.ListField(child=inline_serializer("CommonLcListItem", fields={
                "id": s.CharField(),
                "name": s.CharField(),
                "ig_name": s.CharField(),
                "org_name": s.CharField(allow_null=True),
                "member_count": s.IntegerField(),
                "members": s.ListField(child=s.DictField(), allow_null=True),
                "meet_place": s.CharField(allow_null=True),
                "meet_time": s.CharField(allow_null=True),
                "lead_name": s.CharField(allow_null=True),
                "karma": s.IntegerField(),
            })),
            "pagination": s.DictField(child=s.IntegerField()),
        })},
    )
    def get(self, request):
        all_circles = LearningCircle.objects.all()
        
        ig = request.query_params.get("ig")
        org = request.query_params.get("org")
        district = request.query_params.get("district")

        if district:
            all_circles = all_circles.filter(org__district__name=district)

        if org:
            all_circles = all_circles.filter(org__title=org)

        if ig:
            all_circles = all_circles.filter(ig__name=ig)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            all_circles,
            request,
            search_fields=[],
        )

        serializer = LcListSerializer(
            paginated_queryset.get("queryset"),
            many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get(
                "pagination"
            )
        )

    
class LcDashboardAPI(APIView):
    @extend_schema(tags=['Common'], description="Retrieve Lc Dashboard.",
        responses={200: inline_serializer("CommonLcDashboardResponse", fields={
            "hasError": s.BooleanField(default=False),
            "statusCode": s.IntegerField(default=200),
            "message": s.DictField(child=s.CharField(), default={}),
            "response": inline_serializer("CommonLcDashboardData", fields={
                "lc_count": s.IntegerField(help_text="Total number of learning circles"),
                "total_enrollment": s.IntegerField(help_text="Total college-student enrollments"),
                "circle_count_by_ig": s.ListField(
                    child=inline_serializer("CommonLcDashboardIgStat", fields={
                        "name": s.CharField(),
                        "total_circles": s.IntegerField(),
                        "total_users": s.IntegerField(),
                    }),
                    help_text="Circle and user counts grouped by interest group",
                ),
                "unique_users": s.IntegerField(help_text="Number of unique enrolled users"),
            }),
        })},
    )
    def get(self, request):
        date = request.query_params.get("date")
        if date:
            learning_circle_count = LearningCircle.objects.filter(created_at__gt=date).count()
            # total_no_enrollment = UserCircleLink.objects.filter(accepted=True,
            #                                                     user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            #                                                     created_at__gt=date).count()
            total_no_enrollment = (UserCircleLink.objects.filter(accepted=True,
                                                                 user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                                                                 created_at__gt=date).values(
                full_name=F("user__full_name"),
                email=F("user__email"),
                muid=F("user__muid"),
                circle_name=F("circle__name"),
                district=F("user__user_organization_link_user__org__district__name"),
                circle_ig=F("circle__ig__name"),
                organisation=F("user__user_organization_link_user__org__title"),

            )
            .annotate(
                karma_earned=Sum(
                    "user__karma_activity_log_user__task__karma",
                    filter=Q(
                        user__karma_activity_log_user__task__ig=F("circle__ig")
                    ),
                ),
                dwms_id=Case(
                    When(
                        user__integration_authorization_user__integration__name=IntegrationType.KKEM.value,
                        then=F(
                            "user__integration_authorization_user__additional_field"
                        ),
                    ),
                    default=Value(None, output_field=CharField()),
                    output_field=CharField(),
                ),
            )
            ).count()
            user_circle_link_count = UserCircleLink.objects.filter(created_at__gt=date, circle=OuterRef('pk')).values(
                'circle_id').annotate(
                total_users=Count('id')).values('total_users')

            query = InterestGroup.objects.annotate(
                total_circles=Count("learning_circle_ig", distinct=True),
                total_users=Subquery(user_circle_link_count, output_field=models.IntegerField())
            ).values("name", "total_circles", "total_users")

            circle_count_by_ig = (
                query.values("name")
                .order_by("name")
                .annotate(
                    total_circles=Count("learning_circle_ig", distinct=True),
                    total_users=Count("learning_circle_ig__user_circle_link_circle", distinct=True),
                )
            )
            unique_user_count = (
                UserCircleLink.objects.filter(created_at__gt=date, accepted=True)
                .values("user")
                .distinct()
                .count()
            )
        else:
            learning_circle_count = LearningCircle.objects.all().count()
            # total_no_enrollment = UserCircleLink.objects.filter(accepted=True,
            #                                                     user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value).count()
            total_no_enrollment = (UserCircleLink.objects.filter(accepted=True,
                                                                 user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value).values(
                full_name=F("user__full_name"),
                email=F("user__email"),
                muid=F("user__muid"),
                circle_name=F("circle__name"),
                district=F("user__user_organization_link_user__org__district__name"),
                circle_ig=F("circle__ig__name"),
                organisation=F("user__user_organization_link_user__org__title"),

            )
            .annotate(
                karma_earned=Sum(
                    "user__karma_activity_log_user__task__karma",
                    filter=Q(
                        user__karma_activity_log_user__task__ig=F("circle__ig")
                    ),
                ),
                dwms_id=Case(
                    When(
                        user__integration_authorization_user__integration__name=IntegrationType.KKEM.value,
                        then=F(
                            "user__integration_authorization_user__additional_field"
                        ),
                    ),
                    default=Value(None, output_field=CharField()),
                    output_field=CharField(),
                ),
            )
            ).count()
            user_circle_link_count = UserCircleLink.objects.filter(circle=OuterRef('pk')).values('circle_id').annotate(
                total_users=Count('id')).values('total_users')

            query = InterestGroup.objects.annotate(
                total_circles=Count("learning_circle_ig", distinct=True),
                total_users=Subquery(user_circle_link_count, output_field=models.IntegerField())
            ).values("name", "total_circles", "total_users")

            circle_count_by_ig = (
                query.values("name")
                .order_by("name")
                .annotate(
                    total_circles=Count("learning_circle_ig", distinct=True),
                    total_users=Count("learning_circle_ig__user_circle_link_circle", distinct=True),
                )
            )

            unique_user_count = (
                UserCircleLink.objects.filter(accepted=True)
                .values("user")
                .distinct()
                .count()
            )

        return CustomResponse(
            response={
                "lc_count": learning_circle_count,
                "total_enrollment": total_no_enrollment,
                "circle_count_by_ig": circle_count_by_ig,
                "unique_users": unique_user_count,
            }
        ).get_success_response()


class LcReportAPI(APIView):
    @extend_schema(
        tags=['Common'],
        description="Retrieve Lc Report.",
        responses={200: StudentInfoSerializer},
    )
    def get(self, request):
        date = request.query_params.get('date')
        if date:
            student_info = (UserCircleLink.objects.filter(accepted=True,
                                                          user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                                                          created_at__date=date).values(
                full_name=F("user__full_name"),
                muid=F("user__muid"),
                circle_name=F("circle__name"),
                circle_ig=F("circle__ig__name"),
                organisation=F("user__user_organization_link_user__org__title"),
                dwms_id=Case(
                    When(
                        user__integration_authorization_user__integration__name=IntegrationType.KKEM.value,
                        then=F(
                            "user__integration_authorization_user__additional_field"
                        ),
                    ),
                    default=Value(None, output_field=CharField()),
                    output_field=CharField(),
                ),
            )
            .annotate(
                karma_earned=Sum(
                    "user__karma_activity_log_user__task__karma",
                    filter=Q(
                        user__karma_activity_log_user__task__ig=F("circle__ig")
                    ),
                )
            ))
        else:
            student_info = (
                UserCircleLink.objects.filter(
                    accepted=True,
                    user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                )
                .values(
                    full_name=F("user__full_name"),
                    muid=F("user__muid"),
                    circle_name=F("circle__name"),
                    circle_ig=F("circle__ig__name"),
                    organisation=F("user__user_organization_link_user__org__title"),
                    dwms_id=Case(
                        When(
                            user__integration_authorization_user__integration__name=IntegrationType.KKEM.value,
                            then=F(
                                "user__integration_authorization_user__additional_field"
                            ),
                        ),
                        default=Value(None, output_field=CharField()),
                        output_field=CharField(),
                    ),
                )
                .annotate(
                    karma_earned=Sum(
                        "user__karma_activity_log_user__task__karma",
                        filter=Q(
                            user__karma_activity_log_user__task__ig=F("circle__ig")
                        ),
                    )
                )
            )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            student_info,
            request,
            search_fields=["full_name", "muid", "circle_name", 'circle_ig', "organisation",
                           "karma_earned"],
            sort_fields={"full_name": "full_name", "muid": "muid",
                         "circle_name": "circle_name",
                         "circle_ig": "circle_ig", "organisation": "organisation", "dwms_id": "dwms_id",
                         "karma_earned": "karma_earned"},
        )

        student_info_data = StudentInfoSerializer(
            paginated_queryset.get("queryset"), many=True
        ).data

        return CustomResponse().paginated_response(
            data=student_info_data, pagination=paginated_queryset.get("pagination")
        )


class LcReportDownloadAPI(APIView):
    @extend_schema(
        tags=['Common'],
        description="Retrieve Lc Report Download.",
        responses={200: StudentInfoSerializer},
    )
    def get(self, request):
        student_info = (
            UserCircleLink.objects.filter(
                lead=False,
                accepted=True,
                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .values(
                full_name=F("user__full_name"),
                muid=F("user__muid"),
                circle_name=F("circle__name"),
                circle_ig=F("circle__ig__name"),
                organisation=F("user__user_organization_link_user__org__title"),
                dwms_id=Case(
                    When(
                        user__integration_authorization_user__integration__name=IntegrationType.KKEM.value,
                        then=F(
                            "user__integration_authorization_user__additional_field"
                        ),
                    ),
                    default=Value(None, output_field=CharField()),
                    output_field=CharField(),
                ),
            )
            .annotate(
                karma_earned=Sum(
                    "user__karma_activity_log_user__task__karma",
                    filter=Q(user__karma_activity_log_user__task__ig=F("circle__ig")),
                )
            )
        )

        student_info_data = StudentInfoSerializer(student_info, many=True).data

        return CommonUtils.generate_csv(student_info_data, "Learning Circle Report")


class CollegeWiseLcReport(APIView):
    @extend_schema(
        tags=['Common'],
        description="Retrieve College Wise Lc Report.",
        responses={200: CollegeInfoSerializer},
    )
    def get(self, request):
        date = request.query_params.get('date')
        if date:
            lc_query = (
                LearningCircle.objects.filter(org__org_type=OrganizationType.COLLEGE.value, created_at__date=date)
                .select_related("org")
                .prefetch_related("user_circle_link_circle__user")
            )
            learning_circle_count_subquery = (lc_query.values(org_title=F("org__title"))
                                              .annotate(learning_circle_count=Count("id"))
                                              .filter(org_title=OuterRef("org_title"))
                                              .values("learning_circle_count")
            [:1])
            learning_circles_info = (lc_query.values(org_title=F("org__title"))
                                     .annotate(
                learning_circle_count=Subquery(learning_circle_count_subquery),
                user_count=Count("user_circle_link_circle__user"),
            ).order_by("org_title"))
        else:
            lc_query = (
                LearningCircle.objects.filter(org__org_type=OrganizationType.COLLEGE.value)
                .select_related("org")
                .prefetch_related("user_circle_link_circle__user")
            )
            learning_circle_count_subquery = (lc_query.values(org_title=F("org__title"))
                                              .annotate(learning_circle_count=Count("id"))
                                              .filter(org_title=OuterRef("org_title"))
                                              .values("learning_circle_count")
            [:1])
            learning_circles_info = (lc_query.values(org_title=F("org__title"))
                                     .annotate(
                learning_circle_count=Subquery(learning_circle_count_subquery),
                user_count=Count("user_circle_link_circle__user"),
            ).order_by("org_title"))

        paginated_queryset = CommonUtils.get_paginated_queryset(
            learning_circles_info,
            request,
            search_fields=["org_title", "learning_circle_count", "user_count"],
            sort_fields={"org_title": "org_title", "learning_circle_count": "learning_circle_count",
                         "user_count": "user_count"},
        )

        collegewise_info_data = CollegeInfoSerializer(paginated_queryset.get("queryset"), many=True).data

        return CustomResponse().paginated_response(
            data=collegewise_info_data, pagination=paginated_queryset.get("pagination")
        )


class CollegeWiseLcReportCSV(APIView):
    @extend_schema(
        tags=['Common'],
        description="Retrieve College Wise Lc Report C S V.",
        responses={200: CollegeInfoSerializer},
    )
    def get(self, request):
        learning_circle_count_subquery = (
            LearningCircle.objects.filter(org__org_type=OrganizationType.COLLEGE.value)
            .values(org_title=F("org__title"))
            .annotate(learning_circle_count=Count("id"))
            .filter(org_title=OuterRef("org_title"))
            .values("learning_circle_count")
            [:1]
        )

        learning_circles_info = (
            LearningCircle.objects.filter(org__org_type=OrganizationType.COLLEGE.value)
            .values(org_title=F("org__title"))
            .annotate(
                learning_circle_count=Subquery(learning_circle_count_subquery),
                user_count=Count("user_circle_link_circle__user"),
            )
            .order_by("org_title")
        )
        paginated_queryset = CommonUtils.get_paginated_queryset(
            learning_circles_info,
            request,
            search_fields=["org_title", "learning_circle_count", "user_count"],
            sort_fields={"org_title": "org_title", "learning_circle_count": "learning_circle_count",
                         "user_count": "user_count"},
            is_pagination=False
        )

        lc_report = CollegeInfoSerializer(paginated_queryset, many=True).data

        return CommonUtils.generate_csv(lc_report, "Learning Circle Report")


class LearningCircleEnrollment(APIView):

    @extend_schema(
        tags=['Common'],
        description="Retrieve Learning Circle Enrollment.",
        responses={200: LearningCircleEnrollmentSerializer},
    )
    def get(self, request):
        total_no_enrollment = (UserCircleLink.objects.filter(accepted=True,
                                                             user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value).values(
            full_name=F("user__full_name"),
            email=F("user__email"),
            muid=F("user__muid"),
            circle_name=F("circle__name"),
            district=F("user__user_organization_link_user__org__district__name"),
            circle_ig=F("circle__ig__name"),
            organisation=F("user__user_organization_link_user__org__title"),
        )
        .annotate(
            karma_earned=Sum(
                "user__karma_activity_log_user__task__karma",
                filter=Q(
                    user__karma_activity_log_user__task__ig=F("circle__ig")
                ),
            ),
            dwms_id=Case(
                When(
                    user__integration_authorization_user__integration__name=IntegrationType.KKEM.value,
                    then=F(
                        "user__integration_authorization_user__additional_field"
                    ),
                ),
                default=Value(None, output_field=CharField()),
                output_field=CharField(),
            ),
        )
        )
        paginated_queryset = CommonUtils.get_paginated_queryset(
            total_no_enrollment,
            request,
            search_fields=["full_name", "email", "muid", "circle_name", "district", "circle_ig",
                           "organisation", "karma_earned"],
            sort_fields={"full_name": "full_name", "email": "email", "muid": "muid",
                         "circle_name": "circle_name", "district": "district", "circle_ig": "circle_ig",
                         "organisation": "organisation", "dwms_id": "dwms_id", "karma_earned": "karma_earned"},
            is_pagination=True)
        lc_enrollment = LearningCircleEnrollmentSerializer(paginated_queryset.get('queryset'), many=True).data

        return CustomResponse().paginated_response(
            data=lc_enrollment, pagination=paginated_queryset.get("pagination")
        )


class LearningCircleEnrollmentCSV(APIView):
    @extend_schema(
        tags=['Common'],
        description="Retrieve Learning Circle Enrollment C S V.",
        responses={200: LearningCircleEnrollmentSerializer},
    )
    def get(self, request):
        total_no_enrollment = (UserCircleLink.objects.filter(accepted=True,
                                                             user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value).values(
            full_name=F("user__full_name"),
            email=F("user__email"),
            muid=F("user__muid"),
            circle_name=F("circle__name"),
            district=F("user__user_organization_link_user__org__district__name"),
            circle_ig=F("circle__ig__name"),
            organisation=F("user__user_organization_link_user__org__title"),

        )
        .annotate(
            karma_earned=Sum(
                "user__karma_activity_log_user__task__karma",
                filter=Q(
                    user__karma_activity_log_user__task__ig=F("circle__ig")
                ),
            ),
            dwms_id=Case(
                When(
                    user__integration_authorization_user__integration__name=IntegrationType.KKEM.value,
                    then=F(
                        "user__integration_authorization_user__additional_field"
                    ),
                ),
                default=Value(None, output_field=CharField()),
                output_field=CharField(),
            ),
        )
        )
        paginated_queryset = CommonUtils.get_paginated_queryset(
            total_no_enrollment,
            request,
            search_fields=["full_name", "email", "muid", "circle_name", "district", "circle_ig",
                           "organisation", "karma_earned"],
            sort_fields={"full_name": "full_name", "email": "email", "muid": "muid",
                         "circle_name": "circle_name", "district": "district", "circle_ig": "circle_ig",
                         "organisation": "organisation", "dwms_id": "dwms_id", "karma_earned": "karma_earned"},
            is_pagination=False)

        lc_enrollment = LearningCircleEnrollmentSerializer(paginated_queryset, many=True).data

        return CommonUtils.generate_csv(lc_enrollment, "Learning Enrollment Report")


class GlobalCountAPI(APIView):
    @extend_schema(tags=['Common'], description="Retrieve Global Count.",
        responses={200: inline_serializer("CommonGlobalCountResponse", fields={
            "hasError": s.BooleanField(default=False),
            "statusCode": s.IntegerField(default=200),
            "message": s.DictField(child=s.CharField(), default={}),
            "response": inline_serializer("CommonGlobalCountData", fields={
                "members": s.IntegerField(help_text="Total registered user count"),
                "org_type_counts": s.ListField(
                    child=inline_serializer("CommonOrgTypeCount", fields={
                        "org_type": s.CharField(),
                        "org_count": s.IntegerField(),
                    }),
                    help_text="Count of organisations per type (college, company, community)",
                ),
                "enablers_mentors_count": s.ListField(
                    child=inline_serializer("CommonRoleCount", fields={
                        "role__title": s.CharField(),
                        "role_count": s.IntegerField(),
                    }),
                    help_text="Count of users with enabler / mentor roles",
                ),
                "ig_count": s.IntegerField(help_text="Total interest group count"),
                "learning_circle_count": s.IntegerField(help_text="Total learning circle count"),
            }),
        })},
    )
    def get(self, request):
        members_count = User.objects.all().count()
        org_type_counts = (
            Organization.objects.filter(
                org_type__in=[
                    OrganizationType.COLLEGE.value,
                    OrganizationType.COMPANY.value,
                    OrganizationType.COMMUNITY.value,
                ]
            )
            .values("org_type")
            .annotate(org_count=Coalesce(Count("org_type"), 0))
        )

        enablers_mentors_count = (
            UserRoleLink.objects.filter(
                role__title__in=[RoleType.MENTOR.value, RoleType.ENABLER.value]
            )
            .values("role__title")
            .annotate(role_count=Coalesce(Count("role__title"), 0))
        )

        interest_groups_count = InterestGroup.objects.all().count()
        learning_circles_count = LearningCircle.objects.all().count()

        data = {
            "members": members_count,
            "org_type_counts": org_type_counts,
            "enablers_mentors_count": enablers_mentors_count,
            "ig_count": interest_groups_count,
            "learning_circle_count": learning_circles_count,
        }
        return CustomResponse(response=data).get_success_response()


class GTASANDSHOREAPI(APIView):
    @extend_schema(tags=['Common'], description="Retrieve G T A S A N D S H O R E.",
        responses={200: inline_serializer("CommonGtasandshoreResponse", fields={
            "hasError": s.BooleanField(default=False),
            "statusCode": s.IntegerField(default=200),
            "message": s.DictField(child=s.CharField(), default={}),
            "response": s.DictField(
                child=s.IntegerField(),
                help_text="Map of normalised college name → submission count from devfolio",
            ),
        })},
    )
    def get(self, request):
        response = requests.get('https://devfolio.vez.social/rank')
        if response.status_code == 200:
            # Save JSON response to a local file
            with open('response.json', 'w') as json_file:
                json.dump(response.json(), json_file)

            with open('response.json', 'r') as file:
                data = json.load(file)
        else:
            with open('response.json', 'r') as file:
                data = json.load(file)

        # Create a dictionary to store the grouped data
        grouped_colleges = {}
        for college, count in data.items():
            # Clean the college name by removing spaces and converting to lowercase
            cleaned_college = college.replace(" ", "").lower()

            # Check if the cleaned name already exists in the grouped_colleges dictionary
            if cleaned_college in grouped_colleges:
                # If it exists, add the count to the existing entry
                grouped_colleges[cleaned_college] += int(count)
            else:
                # If it doesn't exist, create a new entry
                grouped_colleges[cleaned_college] = int(count)
        return CustomResponse(response=grouped_colleges).get_success_response()


class UserProfilePicAPI(APIView):
    @extend_schema(tags=['Common'], description="Retrieve User Profile Pic.",
        responses={200: inline_serializer("CommonUserProfilePicResponse", fields={
            "hasError": s.BooleanField(default=False),
            "statusCode": s.IntegerField(default=200),
            "message": s.DictField(child=s.CharField(), default={}),
            "response": inline_serializer("CommonUserProfilePicData", fields={
                "image": s.CharField(allow_null=True, help_text="URL or path to the user's profile picture"),
            }),
        })},
    )
    def get(self, request, muid):
        user = User.objects.filter(muid=muid).annotate(image=F("profile_pic")).values("image")
        return CustomResponse(response=user).get_success_response()


class ListIGAPI(APIView):

    @extend_schema(tags=['Common'], description="Retrieve List I G.",
        responses={200: inline_serializer("CommonListIGResponse", fields={
            "hasError": s.BooleanField(default=False),
            "statusCode": s.IntegerField(default=200),
            "message": s.DictField(child=s.CharField(), default={}),
            "response": s.ListField(
                child=inline_serializer("CommonListIGItem", fields={
                    "name": s.CharField(help_text="Interest group name"),
                }),
                help_text="All interest groups",
            ),
        })},
    )
    def get(self, request):
        return CustomResponse(response=InterestGroup.objects.all().values("name")).get_success_response()

class IGDetailAPI(APIView):
    @extend_schema(
        tags=['Common'],
        description="Retrieve I G Detail.",
        responses={200: InterestGroupSerializer},
    )
    def get(self, request, pk):
        from api.dashboard.ig.dash_ig_serializer import InterestGroupSerializer

        ig_data = (
            InterestGroup.objects.prefetch_related("user_ig_link_ig")
            .filter(id=pk)
            .first()
        )

        if not ig_data:
            return CustomResponse(
                general_message="Interest Group Not Found"
            ).get_failure_response()

        serializer = InterestGroupSerializer(ig_data, many=False)
        return CustomResponse(
            response={"interestGroup": serializer.data}
        ).get_success_response()
class ListAllLevelInfo(APIView):
    @extend_schema(tags=['Common'], description="Retrieve List All Level Info.",
        responses={200: inline_serializer("CommonListAllLevelInfoResponse", fields={
            "hasError": s.BooleanField(default=False),
            "statusCode": s.IntegerField(default=200),
            "message": s.DictField(child=s.CharField(), default={}),
            "response": s.ListField(
                child=inline_serializer("CommonLevelItem", fields={
                    "name": s.CharField(help_text="Level name"),
                    "tasks": s.ListField(
                        child=inline_serializer("CommonLevelTask", fields={
                            "task_name": s.CharField(),
                            "discord_link": s.CharField(allow_null=True),
                            "hashtag": s.CharField(allow_null=True),
                            "active": s.BooleanField(),
                            "completed": s.BooleanField(),
                            "karma": s.IntegerField(),
                            "task_description": s.CharField(allow_null=True),
                            "interest_group": inline_serializer("CommonLevelTaskIG", fields={
                                "id": s.CharField(allow_null=True),
                                "name": s.CharField(allow_null=True),
                            }),
                            "submission_channel": inline_serializer("CommonLevelTaskChannel", fields={
                                "id": s.CharField(allow_null=True),
                                "name": s.CharField(allow_null=True),
                                "discord_id": s.CharField(allow_null=True),
                            }),
                        }),
                    ),
                }),
                help_text="Levels with their associated tasks",
            ),
        })},
    )
    def get(self, request):

        levels = Level.objects.all().order_by("level_order")
        response = []
        for level in levels:
            tasks = TaskList.objects.filter(level=level, active=True).select_related("ig", "channel")
            task_list = []
            for task in tasks:
                task_list.append({
                    "task_name": task.title,
                    "discord_link": getattr(task, "discord_link", ""),
                    "hashtag": getattr(task, "hashtag", ""),
                    "active": getattr(task, "active", False),
                    "completed": False,  # You can update this logic as needed
                    "karma": getattr(task, "karma", 0),
                    "task_description": getattr(task, "description", None),
                    "interest_group": {
                        "id": getattr(task.ig, "id", None) if task.ig else None,
                        "name": getattr(task.ig, "name", None) if task.ig else None
                    },
                    "submission_channel": {
                        "id": str(getattr(task.channel, "id", "")) if task.channel else None,
                        "name": getattr(task.channel, "name", None) if task.channel else None,
                        "discord_id": getattr(task.channel, "discord_id", None) if task.channel else None
                    }
                })
            response.append({
                "name": level.name,
                "tasks": task_list
            })
        return CustomResponse(response=response).get_success_response()

class ListTopIgUsersAPI(APIView):

    @extend_schema(tags=['Common'], description="Retrieve List Top Ig Users.",
        responses={200: inline_serializer("CommonListTopIgUsersResponse", fields={
            "hasError": s.BooleanField(default=False),
            "statusCode": s.IntegerField(default=200),
            "message": s.DictField(child=s.CharField(), default={}),
            "response": s.ListField(
                child=inline_serializer("CommonTopIgUserItem", fields={
                    "userid": s.CharField(help_text="User UUID"),
                    "muid": s.CharField(help_text="User unique identifier"),
                    "full_name": s.CharField(),
                    "ig_karma": s.IntegerField(help_text="Total karma earned in the requested interest groups"),
                    "igs": s.ListField(
                        child=s.CharField(),
                        help_text="All interest group names the user belongs to",
                    ),
                }),
                help_text="Top 100 users ranked by karma in the requested interest groups",
            ),
        })},
    )
    def get(self, request):
        ig_name = request.query_params.getlist("ig_name", [])

        user_karma_by_ig = KarmaActivityLog.objects.filter(
            task__ig__name__in=ig_name, appraiser_approved=True
        ).values(
            userid=F('user__id'),
            muid=F('user__muid'),
            full_name=F('user__full_name'),
        ).annotate(
            ig_karma=Sum('karma')
        ).order_by('-ig_karma')[:100]

        # Extract 'userid' values into a new list
        userid_list = [entry['userid'] for entry in user_karma_by_ig]

        # Fetch user muid and interest group as a list
        results = UserIgLink.objects.filter(user__id__in=userid_list).values_list('user__muid', 'ig__name',
                                                                                  named=True)

        # Process the results to create the desired structure
        user_ig_dict = {}
        for result in results:
            muid = result.user__muid
            ig = result.ig__name

            if muid not in user_ig_dict:
                user_ig_dict[muid] = {'muid': muid, 'igs': [ig]}
            else:
                user_ig_dict[muid]['igs'].append(ig)

        # Iterate through user_karma_by_ig and add 'igs' information
        for user_karma in user_karma_by_ig:
            muid = user_karma['muid']
            if muid in user_ig_dict:
                user_karma['igs'] = user_ig_dict[muid]['igs']
            else:
                user_karma['igs'] = []

        return CustomResponse(response=user_karma_by_ig).get_success_response()


class BekenAPI(APIView):
    @extend_schema(
        tags=['Common'],
        description="Retrieve Beken.",
        responses={200: UserLeaderboardSerializer},
    )
    def get(self, request):
        user_info = User.objects.exclude(
            user_role_link_user__role__title__in=[RoleType.ENABLER.value, RoleType.MENTOR.value]).order_by(
            '-wallet_user__karma')[:100]
        data = UserLeaderboardSerializer(user_info, many=True)
        return CustomResponse(response=data.data).get_success_response()


class LcCollegeAPI(APIView):
    @extend_schema(
        tags=['Common'],
        description="Retrieve Lc College.",
        responses={200: OrgSerializer},
    )
    def get(self, request):
        org_queryset = Organization.objects.filter(
            Q(org_type=OrganizationType.COLLEGE.value),
            Q(district_id=request.query_params.get("district_id")),
        )
        department_queryset = Department.objects.all()

        college_serializer_data = OrgSerializer(
            org_queryset, many=True
        ).data

        department_serializer_data = OrgSerializer(
            department_queryset, many=True
        ).data

        return CustomResponse(
            response={
                "colleges": college_serializer_data,
                "departments": department_serializer_data,
            }
        ).get_success_response()



class LcDistrictAPI(APIView):
    @extend_schema(
        tags=['Common'],
        description="Retrieve Lc District.",
        responses={200: DistrictSerializer},
    )
    def get(self, request):
        district = District.objects.filter(zone__state_id=request.query_params.get("state_id"))
        
        serializer = DistrictSerializer(district, many=True)

        return CustomResponse(
            response={
                "districts": serializer.data,
            }
        ).get_success_response()

class LcStateAPI(APIView):
    @extend_schema(
        tags=['Common'],
        description="Retrieve Lc State.",
        responses={200: StateSerializer},
    )
    def get(self, request):
        
        state = State.objects.filter(country_id=request.query_params.get("country_id"))
        serializer = StateSerializer(state, many=True)
        
        return CustomResponse(
            response={
                "states": serializer.data,
            }
        ).get_success_response()


class LcCountryAPI(APIView):
    @extend_schema(
        tags=['Common'],
        description="Retrieve Lc Country.",
        responses={200: CountrySerializer},
    )
    def get(self, request):
        countries = Country.objects.all()

        serializer = CountrySerializer(countries, many=True)

        return CustomResponse(
            response={
                "countries": serializer.data,
            }
        ).get_success_response()



