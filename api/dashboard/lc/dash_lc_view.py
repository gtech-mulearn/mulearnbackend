from rest_framework.views import APIView
import uuid
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType , OrganizationType
from db.task import InterestGroup
from db.organization import UserOrganizationLink , Organization
from utils.utils import DateTimeUtils
from db.learning_circle import LearningCircle , UserCircleLink
from .dash_lc_serializer import LearningCircleSerializer
class LearningCircleAPI(APIView):
    authentication_classes = [CustomizePermission]
    def get(self, request): #lists the learning circle in the user's college
        user_id = JWTUtils.fetch_user_id(request)
        org_id = UserOrganizationLink.objects.filter(user_id=user_id, org__org_type=OrganizationType.COLLEGE.value).values_list('org_id',
                                                                                                           flat=True).first()
        learning_queryset = LearningCircle.objects.filter(org=org_id)
        learning_serializer = LearningCircleSerializer(learning_queryset, many=True)
        return CustomResponse(response=learning_serializer.data).get_success_response()
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
