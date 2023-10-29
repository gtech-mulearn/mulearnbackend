from django.db.models import Sum, F, Case, When, Value, CharField, Count, Q
from django.db.models.functions import Coalesce
from rest_framework.views import APIView

from db.learning_circle import LearningCircle
from db.learning_circle import UserCircleLink
from db.organization import Organization
from db.task import InterestGroup
from db.user import User, UserRoleLink
from utils.response import CustomResponse
from utils.types import IntegrationType, OrganizationType, RoleType
from utils.utils import CommonUtils
from .serializer import StudentInfoSerializer


class LcDashboardAPI(APIView):
    def get(self, request):
        date = request.GET.get("date")
        if date:
            learning_circle_count = LearningCircle.objects.filter(
                created_at__gt=date
            ).count()
        else:
            learning_circle_count = LearningCircle.objects.all().count()

        total_no_enrollment = UserCircleLink.objects.filter(accepted=True).count()
        query = InterestGroup.objects.annotate(
            total_circles=Count("learningcircle"),
            total_users=Count("learningcircle__usercirclelink__user", distinct=True),
        ).values("name", "total_circles", "total_users")
        circle_count_by_ig = (
            query.values("name")
            .order_by("name")
            .annotate(
                total_circles=Count("learningcircle", distinct=True),
                total_users=Count(
                    "learningcircle__usercirclelink__user", distinct=True
                ),
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
        date = request.GET.get("date")
        if date:
            student_info = (
                UserCircleLink.objects.filter(
                    accepted=True,
                    user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                    created_at=date,
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
            search_fields=["first_name", "last_name", "muid"],
            sort_fields={"first_name": "first_name", "muid": "muid"},
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


class CollegeWiseLcReport(APIView):
    def get(self, request):
        learning_circles_info = (
            LearningCircle.objects.filter(org__org_type=OrganizationType.COLLEGE.value)
            .values(org_title=F("org__title"))
            .annotate(
                learning_circle_count=Count("id"), user_count=Count("usercirclelink")
            )
            .order_by("org_title")
        )

        return CustomResponse(response=learning_circles_info).get_success_response()


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
