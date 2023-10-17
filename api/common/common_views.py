from django.db.models import Sum, F, Case, When, Value, CharField, Count, Q
from django.db.models.functions import Coalesce
from rest_framework.views import APIView

from db.learning_circle import LearningCircle
from db.learning_circle import UserCircleLink
from db.organization import Organization
from db.task import InterestGroup
from db.user import User, UserRoleLink
from utils.response import CustomResponse
from utils.types import IntegrationType, OrganizationType
from utils.utils import CommonUtils
from .serializer import StudentInfoSerializer
from collections import defaultdict

class LcDashboardAPI(APIView):

    def get(self, request):
        date = request.GET.get('date')
        if date:
            learning_circle_count = LearningCircle.objects.filter(created_at__gt=date).count()
            total_no_enrollment = UserCircleLink.objects.filter(accepted=True, created_at__gt=date).count()
            circle_count_by_ig = LearningCircle.objects.filter(created_at__gt=date).values(
                ig_name=F('ig__name')).annotate(total_circles=Count('id'),
                                                total_users=Count('ig__learningcircle__usercirclelink__user',
                                                                  distinct=True))
            unique_user_count = UserCircleLink.objects.filter(accepted=True, created_at__gt=date).values(
                'user').distinct().count()
        else:
            learning_circle_count = LearningCircle.objects.all().count()
            total_no_enrollment = UserCircleLink.objects.filter(accepted=True).count()
            circle_count_by_ig = LearningCircle.objects.all().values(ig_name=F('ig__name')).annotate(
                total_circles=Count('id'), total_users=Count('ig__learningcircle__usercirclelink__user', distinct=True))

            unique_user_count = UserCircleLink.objects.filter(accepted=True).values('user').distinct().count()
        return CustomResponse(response={'lc_count': learning_circle_count, 'total_enrollment': total_no_enrollment,
                                        'circle_count_by_ig': circle_count_by_ig,
                                        'unique_users': unique_user_count}).get_success_response()


class LcReportAPI(APIView):

    def get(self, request):
        date = request.GET.get('date')
        if date:
            student_info = UserCircleLink.objects.filter(
                accepted=True,
                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                created_at=date,
            ).values(
                first_name=F('user__first_name'),
                last_name=F('user__last_name'),
                muid=F('user__muid'),
                circle_name=F('circle__name'),
                circle_ig=F('circle__ig__name'),
                organisation=F('user__user_organization_link_user__org__title'),
                dwms_id=Case(
                    When(
                        user__integration_authorization_user__integration__name=IntegrationType.KKEM.value,
                        then=F('user__integration_authorization_user__additional_field')
                    ),
                    default=Value(None, output_field=CharField()),
                    output_field=CharField()
                )
            ).annotate(karma_earned=Sum('user__karma_activity_log_user__task__karma',
                                        filter=Q(user__karma_activity_log_user__task__ig=F('circle__ig'))))
        else:
            student_info = UserCircleLink.objects.filter(
                accepted=True,
                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value
            ).values(
                first_name=F('user__first_name'),
                last_name=F('user__last_name'),
                muid=F('user__muid'),
                circle_name=F('circle__name'),
                circle_ig=F('circle__ig__name'),
                organisation=F('user__user_organization_link_user__org__title'),
                dwms_id=Case(
                    When(
                        user__integration_authorization_user__integration__name=IntegrationType.KKEM.value,
                        then=F('user__integration_authorization_user__additional_field')
                    ),
                    default=Value(None, output_field=CharField()),
                    output_field=CharField()
                )
            ).annotate(karma_earned=Sum('user__karma_activity_log_user__task__karma',
                                        filter=Q(user__karma_activity_log_user__task__ig=F('circle__ig'))))

        paginated_queryset = CommonUtils.get_paginated_queryset(student_info, request,
                                                                search_fields=['first_name', 'last_name', 'muid'],
                                                                sort_fields={'first_name': 'first_name',
                                                                             'muid': 'muid'})

        student_info_data = StudentInfoSerializer(paginated_queryset.get('queryset'), many=True).data

        return CustomResponse().paginated_response(data=student_info_data,
                                                   pagination=paginated_queryset.get('pagination'))


class LcReportDownloadAPI(APIView):

    def get(self, request):
        student_info = UserCircleLink.objects.filter(lead=False, accepted=True,
                                                     user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value).values(
            first_name=F('user__first_name'),
            last_name=F('user__last_name'),
            muid=F('user__muid'),
            circle_name=F('circle__name'),
            circle_ig=F('circle__ig__name'),
            organisation=F('user__user_organization_link_user__org__title'),
            dwms_id=Case(
                When(
                    user__integration_authorization_user__integration__name=IntegrationType.KKEM.value,
                    then=F('user__integration_authorization_user__additional_field')
                ),
                default=Value(None, output_field=CharField()),
                output_field=CharField()
            )
        ).annotate(karma_earned=Sum('user__karma_activity_log_user__task__karma',
                                    filter=Q(user__karma_activity_log_user__task__ig=F('circle__ig'))))

        student_info_data = StudentInfoSerializer(student_info, many=True).data

        return CommonUtils.generate_csv(student_info_data, "Learning Circle Report")


class CollegeWiseLcReport(APIView):

    def get(self, request):
        learning_circles_info = LearningCircle.objects.filter(org__org_type=OrganizationType.COLLEGE.value) \
            .values('org__title', 'name') \
            .annotate(user_count=Count('usercirclelink')) \
            .order_by('org__title')

        org_learning_circles = defaultdict(list)

        for info in learning_circles_info:
            org_name = info['org__title']
            org_learning_circles[org_name].append({
                'name': info['name'],
                'user_count': info['user_count']
            })

        result_list = [{"org_name": org_name, "learning_circles": circles} for org_name, circles in
                       org_learning_circles.items()]

        return CustomResponse(response=result_list).get_success_response()


class GlobalCountAPI(APIView):

    def get(self, request):
        members_count = User.objects.all().count()
        org_type_counts = Organization.objects.filter(
            org_type__in=[OrganizationType.COLLEGE.value, OrganizationType.COMPANY.value,
                          OrganizationType.COMMUNITY.value]
        ).values('org_type').annotate(org_count=Coalesce(Count('org_type'), 0))

        enablers_mentors_count = UserRoleLink.objects.filter(role__title__in=["Mentor", "Enabler"]).values(
            'role__title').annotate(role_count=Coalesce(Count('role__title'), 0))

        interest_groups_count = InterestGroup.objects.all().count()
        learning_circles_count = LearningCircle.objects.all().count()

        data = {
            'members': members_count,
            'org_type_counts': org_type_counts,
            'enablers_mentors_count': enablers_mentors_count,
            'ig_count': interest_groups_count,
            'learning_circle_count': learning_circles_count
        }
        return CustomResponse(response=data).get_success_response()
