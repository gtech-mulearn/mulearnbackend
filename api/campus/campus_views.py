from rest_framework.views import APIView
from api.register.serializers import UserSerializer
from db.organization import Organization, UserOrganizationLink
from db.task import TotalKarma
from db.user import User
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from .serializers import UserOrgSerializer


class StudentDetails(APIView):
    authentication_classes = [CustomizePermission]

    # @RoleRequired(roles=[RoleType.CAMPUS_AMBASSADOR])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = UserOrganizationLink.objects.filter(
            user_id=user_id, org__org_type=OrganizationType.COLLEGE.value).first()
        user_org_links = UserOrganizationLink.objects.filter(org_id=user_org_link.org_id)
        # print(user_org_links)
        users_total_karma = TotalKarma.objects.all()
        hey = UserOrgSerializer(users_total_karma, many=True).data

        return CustomResponse(response=hey).get_success_response()
    
    # response:{
    #     "name":"",
    #     "email":"",
    #     "phone":"",
    #     "karma":"",
    #     "rank":""
    # }

class CollegeDetails(APIView):
    authentication_classes = [CustomizePermission]

    # response:{
    #     "totalkarma":"",
    #     "totalmember":"",
    #     "activemembers":"",
    #     "rank":"",
    #     "name":"",
    #     "campuscode":"",
    #     "campuszone":"",
    #     "campuslead":""
    # }