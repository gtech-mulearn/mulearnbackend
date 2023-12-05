import json

import requests
from django.db import models
from django.db.models import Subquery, OuterRef
from django.db.models import Sum, F, Case, When, Value, CharField, Count, Q
from django.db.models.functions import Coalesce
from rest_framework.views import APIView

from db.learning_circle import LearningCircle
from db.learning_circle import UserCircleLink
from db.organization import Organization
from db.task import InterestGroup, KarmaActivityLog, UserIgLink
from db.user import User, UserRoleLink
from utils.response import CustomResponse
from utils.types import IntegrationType, OrganizationType, RoleType
from utils.utils import CommonUtils
from .serializer import StudentInfoSerializer, CollegeInfoSerializer, LearningCircleEnrollmentSerializer


class LcDashboardAPI(APIView):
    def get(self, request):
        date = request.query_params.get("date")
        if date:
            learning_circle_count = LearningCircle.objects.filter(created_at__gt=date).count()
            total_no_enrollment = UserCircleLink.objects.filter(accepted=True,
                                                                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                                                                created_at__gt=date).count()
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
            total_no_enrollment = UserCircleLink.objects.filter(accepted=True,
                                                                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value).count()

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
    def get(self, request):
        date = request.query_params.get('date')
        if date:
            student_info = (UserCircleLink.objects.filter(accepted=True,
                                                          user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                                                          created_at__date=date).values(
                first_name=F("user__first_name"),
                last_name=F("user__last_name"),
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
                    first_name=F("user__first_name"),
                    last_name=F("user__last_name"),
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
            search_fields=["first_name", "last_name", "muid", "circle_name", 'circle_ig', "organisation",
                           "karma_earned"],
            sort_fields={"first_name": "first_name", "last_name": "last_name", "muid": "muid",
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
    def get(self, request):
        student_info = (
            UserCircleLink.objects.filter(
                lead=False,
                accepted=True,
                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .values(
                first_name=F("user__first_name"),
                last_name=F("user__last_name"),
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


class CollegeWiseLcReportCSV(APIView):
    def get(self, request):
        learning_circles_info = (
            LearningCircle.objects.filter(org__org_type=OrganizationType.COLLEGE.value)
            .values(org_title=F("org__title"))
            .annotate(
                learning_circle_count=Count("id"), user_count=Count("user_circle_link_circle")
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


class CollegeWiseLcReport(APIView):
    def get(self, request):
        date = request.query_params.get('date')
        if date:
            learning_circles_info = (
                LearningCircle.objects.filter(org__org_type=OrganizationType.COLLEGE.value, created_at__date=date)
                .values(org_title=F("org__title"))
                .annotate(
                    learning_circle_count=Count("id"), user_count=Count("user_circle_link_user")
                )
                .order_by("org_title")
            )
        else:
            learning_circles_info = (
                LearningCircle.objects.filter(org__org_type=OrganizationType.COLLEGE.value)
                .values(org_title=F("org__title"))
                .annotate(
                    learning_circle_count=Count("id"), user_count=Count("user_circle_link_user")
                )
                .order_by("org_title")
            )

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


class LearningCircleEnrollment(APIView):

    def get(self, request):
        total_no_enrollment = (UserCircleLink.objects.filter(accepted=True,
                                                             user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value).values(
            first_name=F("user__first_name"),
            last_name=F("user__last_name"),
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
            search_fields=["first_name", "last_name", "email", "muid", "circle_name", "district", "circle_ig",
                           "organisation", "karma_earned"],
            sort_fields={"first_name": "first_name", "last_name": "last_name", "email": "email", "muid": "muid",
                         "circle_name": "circle_name", "district": "district", "circle_ig": "circle_ig",
                         "organisation": "organisation", "dwms_id": "dwms_id", "karma_earned": "karma_earned"},
            is_pagination=False)
        lc_enrollment = LearningCircleEnrollmentSerializer(paginated_queryset.get('queryset'), many=True).data

        return CustomResponse().paginated_response(
            data=lc_enrollment, pagination=paginated_queryset.get("pagination")
        )


class LearningCircleEnrollmentCSV(APIView):
    def get(self, request):
        total_no_enrollment = (UserCircleLink.objects.filter(accepted=True,
                                                             user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value).values(
            first_name=F("user__first_name"),
            last_name=F("user__last_name"),
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
            search_fields=["first_name", "last_name", "email", "muid", "circle_name", "district", "circle_ig",
                           "organisation", "karma_earned"],
            sort_fields={"first_name": "first_name", "last_name": "last_name", "email": "email", "muid": "muid",
                         "circle_name": "circle_name", "district": "district", "circle_ig": "circle_ig",
                         "organisation": "organisation", "dwms_id": "dwms_id", "karma_earned": "karma_earned"},
            is_pagination=False)

        lc_enrollment = LearningCircleEnrollmentSerializer(paginated_queryset, many=True).data

        return CommonUtils.generate_csv(lc_enrollment, "Learning Enrollment Report")


class GlobalCountAPI(APIView):
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
    def get(self, request, muid):
        user = User.objects.filter(muid=muid).annotate(image=F("profile_pic")).values("image")
        return CustomResponse(response=user).get_success_response()


class ListIGAPI(APIView):

    def get(self, request):
        return CustomResponse(response=InterestGroup.objects.all().values("name")).get_success_response()


class ListTopIgUsersAPI(APIView):

    def get(self, request):
        ig_name = request.query_params.getlist("ig_name", [])

        user_karma_by_ig = KarmaActivityLog.objects.filter(
            task__ig__name__in=ig_name, appraiser_approved=True
        ).values(
            userid=F('user__id'),
            muid=F('user__muid'),
            first_name=F('user__first_name'),
            last_name=F('user__last_name'),
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
