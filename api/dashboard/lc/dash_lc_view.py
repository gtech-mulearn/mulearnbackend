from rest_framework.views import APIView
import uuid
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType , OrganizationType
from db.task import InterestGroup
from db.organization import UserOrganizationLink , Organization
from utils.utils import DateTimeUtils
from db.learning_circle import LearningCircle , UserCircleLink
from db.task import TotalKarma
from .dash_lc_serializer import LearningCircleSerializer
from django.db.models import Sum
class LearningCircleAPI(APIView):
    authentication_classes = [CustomizePermission]
    def get(self, request): #lists the learning circle in the user's college
        user_id = JWTUtils.fetch_user_id(request)
        org_id = UserOrganizationLink.objects.filter(user_id=user_id, org__org_type=OrganizationType.COLLEGE.value).values_list('org_id',
                                                                                                           flat=True).first()
        learning_queryset = LearningCircle.objects.filter(org=org_id)
        learning_serializer = LearningCircleSerializer(learning_queryset, many=True)
        learning_circle_data = learning_serializer.data
        for circle_data in learning_circle_data:
            circle_id = circle_data['id']
            member_count = UserCircleLink.objects.filter(circle_id=circle_id).count()
            circle_data['member_count'] = member_count
        return CustomResponse(response=learning_circle_data).get_success_response()

    @role_required([RoleType.ADMIN.value, ])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        org_link = UserOrganizationLink.objects.filter(user_id=user_id,
                                                       org__org_type=OrganizationType.COLLEGE.value).first()
        lc_data = LearningCircle.objects.create(
            id=uuid.uuid4(),
            name=request.data.get('name'),
            circle_code=request.data.get('circle_code'),
            ig_id= InterestGroup.objects.filter(name=request.data.get('ig')).values_list('id', flat=True).first(),
            org = org_link.org,
            updated_by_id=user_id,
            updated_at=DateTimeUtils.get_current_utc_time(),
            created_by_id=user_id,
            created_at=DateTimeUtils.get_current_utc_time())

        UserCircleLink.objects.create(
            id=uuid.uuid4(),
            user=org_link.user,
            circle=lc_data,
            lead_id=user_id,
            accepted=1,
            accepted_at=DateTimeUtils.get_current_utc_time(),
            created_at=DateTimeUtils.get_current_utc_time()
        )
        serializer = LearningCircleSerializer(lc_data)
        return CustomResponse(response={"interstGroup": serializer.data}).get_success_response()

class LearningCircleListApi(APIView):
    authentication_classes = [CustomizePermission]
    def get(self, request): #Lists user's learning circle
        user_id = JWTUtils.fetch_user_id(request)
        learning_queryset = LearningCircle.objects.filter(usercirclelink__user_id=user_id)
        learning_serializer = LearningCircleSerializer(learning_queryset, many=True)
        return CustomResponse(response={"User_id": learning_serializer.data}).get_success_response()

class LearningCircleHomeApi(APIView):
    authentication_classes = [CustomizePermission]
    def get(self, request,circle_id):
        user_id = JWTUtils.fetch_user_id(request)
        learning_circle = LearningCircle.objects.filter(id=circle_id).first()
        learning_circle_data = {
            'circle': learning_circle.name,
            'circle_code': learning_circle.circle_code,
            'college': learning_circle.org.title,
            'members': [],
            'rank': 3,
            'total_karma': TotalKarma.objects.filter(user__usercirclelink__circle=learning_circle)
                           .aggregate(total_karma=Sum('karma'))['total_karma'] or 0,
        }
        members = UserCircleLink.objects.filter(circle=learning_circle)
        for member in members:
            member_data = {
                'username': f'{member.user.first_name} {member.user.last_name}'
                if member.user.last_name
                else member.user.first_name,
                'profile_pic': member.user.profile_pic or None,
                'karma': TotalKarma.objects.filter(user=member.user.id)
                .values_list('karma', flat=True)
                .first(),
            }
            learning_circle_data['members'].append(member_data)
        return CustomResponse(response=learning_circle_data).get_success_response()