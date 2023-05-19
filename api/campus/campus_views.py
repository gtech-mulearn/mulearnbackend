from rest_framework.views import APIView

from db.organization import UserOrganizationLink
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from .serializers import CollegeSerializer, UserOrgSerializer


class StudentDetails(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.CAMPUS_AMBASSADOR])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = UserOrganizationLink.objects.filter(
            user_id=user_id, org__org_type=OrganizationType.COLLEGE.value).first()
        user_org_links = UserOrganizationLink.objects.filter(
            org_id=user_org_link.org_id)
        serializer = UserOrgSerializer(user_org_links, many=True)
        serialized_data = serializer.data
        return CustomResponse(response=serialized_data).get_success_response()


class CampusDetails(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.CAMPUS_AMBASSADOR])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = UserOrganizationLink.objects.filter(
            user_id=user_id, org__org_type=OrganizationType.COLLEGE.value).first()
        serializer = CollegeSerializer(user_org_link, many=False).data
        return CustomResponse(response=serializer).get_success_response()
