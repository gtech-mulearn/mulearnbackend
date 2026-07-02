from rest_framework.views import APIView
from django.db.models import Sum, Count, F, Q

from utils.response import CustomResponse
from db.organization import Organization, UserOrganizationLink
from db.task import UserIgLink
from db.learning_circle import LearningCircle
from utils.types import OrganizationType
from api.dashboard.campus.serializers import CampusDetailsPublicSerializer
from rest_framework.throttling import AnonRateThrottle

class CampusDetailsRateThrottle(AnonRateThrottle):
    rate = '60/minute'

class CollegeDetailsAPI(APIView):
    throttle_classes = [CampusDetailsRateThrottle]

    def get(self, request, college_code):
        # 1. Basic campus details & MuLearn details
        org = Organization.objects.filter(code=college_code, org_type=OrganizationType.COLLEGE.value).first()
        if org is None:
            return CustomResponse(general_message="College not found").get_failure_response()

        campus_details = CampusDetailsPublicSerializer(org, many=False).data

        # 2. Top 20 learner leaderboard with karma
        top_20_learners_data = []
        top_20_learners_qs = UserOrganizationLink.objects.filter(
            org=org,
            verified=True,
            user__wallet_user__isnull=False
        ).select_related('user', 'user__wallet_user').order_by('-user__wallet_user__karma')[:20]

        for link in top_20_learners_qs:
            top_20_learners_data.append({
                "full_name": link.user.full_name,
                "muid": link.user.muid,
                "karma": link.user.wallet_user.karma,
                "profile_pic": link.user.profile_pic
            })

        # 3. Campus IG details
        ig_details = UserIgLink.objects.filter(
            user__user_organization_link_user__org=org,
            user__user_organization_link_user__verified=True
        ).values(
            ig_name=F('ig__name'),
            ig_code=F('ig__code')
        ).annotate(
            members=Count('user', distinct=True),
            total_karma=Sum('user__wallet_user__karma')
        ).order_by('-members')

        # 4. Campus Learning Circle details
        lc_details = LearningCircle.objects.filter(
            org=org
        ).values(
            'title',
            ig_code=F('ig__code'),
            ig_name=F('ig__name')
        ).annotate(
            members=Count('user_circle_link_circle', filter=Q(user_circle_link_circle__accepted=True), distinct=True)
        ).order_by('-members')

        data = {
            "campus_details": campus_details,
            "top_learners": top_20_learners_data,
            "ig_details": ig_details,
            "lc_details": lc_details
        }

        return CustomResponse(response=data).get_success_response()
