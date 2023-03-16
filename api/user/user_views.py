from rest_framework.views import APIView
from api.user.serializers import AreaOfInterstAPISerializer, OrgSerializer, RegisterSerializer, UserDetailSerializer
from organization.models import Country, Department, Organization, State, Zone, District
from rest_framework import viewsets
from task.models import InterestGroup
from user.models import Role, User

from utils.utils_views import CustomResponse, CustomizePermission


class RegisterJWTValidte(APIView):
    authentication_classes = [CustomizePermission]
    print(authentication_classes)

    def get(self, request):
        discord_id = request.auth.get('id', None)
        if User.objects.filter(discord_id=discord_id).exists():
            return CustomResponse(has_error=True, message='You are already registerd', status_code=400).get_failure_response()
        return CustomResponse(response={'token': True}).get_success_response()


class RegisterData(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request):
        data = request.data
        create_user = RegisterSerializer(
            data=data, context={'request': request})
        if create_user.is_valid():
            user_obj = create_user.save()
            return CustomResponse(response={"data": UserDetailSerializer(user_obj, many=False).data}).get_success_response()
        else:
            return CustomResponse(has_error=True, status_code=400, message=create_user.errors).get_failure_response()
        return CustomResponse(response={'token': data}).get_success_response()


# class CountryAPI(APIView):
#     authentication_classes = [CustomizePermission]

#     def get(self, request):
#         queryset = Country.objects.all()
#         read_serializer_data = CountrySerializer(queryset, many=True).data
#         countries = []
#         for data in read_serializer_data:
#             countries = [data['name']]
#         return CustomResponse(response=countries).get_success_response()

class RoleAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        roles = ['Student', 'Mentor', 'Enabler']
        role_serializer = Role.objects.filter(title__in=roles)
        role_serializer_data = OrgSerializer(
            role_serializer, many=True).data
        return CustomResponse(response={"roles": role_serializer_data}).get_success_response()


class CollegeAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        org_queryset = Organization.objects.filter(org_type="college")
        department_queryset = Department.objects.all()
        college_serializer_data = OrgSerializer(org_queryset, many=True).data
        department_serializer_data = OrgSerializer(
            department_queryset, many=True).data
        return CustomResponse(response={"colleges": college_serializer_data, "departments": department_serializer_data}).get_success_response()


class CompanyAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        company_queryset = Organization.objects.filter(org_type="company")
        company_serializer_data = OrgSerializer(
            company_queryset, many=True).data
        return CustomResponse(response={"companies": company_serializer_data}).get_success_response()


class ComunityAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        community_queryset = Organization.objects.filter(org_type="comunity")
        comunity_serializer_data = OrgSerializer(
            community_queryset, many=True).data
        return CustomResponse(response={"communities": comunity_serializer_data}).get_success_response()


class AreaOfInterstAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        aoi_queryset = InterestGroup.objects.all()
        comunity_serializer_data = AreaOfInterstAPISerializer(
            aoi_queryset, many=True).data
        return CustomResponse(response={"aois": comunity_serializer_data}).get_success_response()
