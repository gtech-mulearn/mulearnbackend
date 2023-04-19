from rest_framework.views import APIView

from organization.models import Organization, District
from .serializers import OrganisationSerializer
from utils.utils_views import CustomResponse


class GetInstitutions(APIView):

    def get(self, request, organisation_type):
        organisations = Organization.objects.filter(org_type=organisation_type)
        organisation_serializer = OrganisationSerializer(organisations, many=True)
        return CustomResponse(response={'institutions': organisation_serializer.data}).get_success_response()

    def post(self, request, organisation_type):
        district_name = request.data.get("district")
        district = District.objects.filter(name=district_name).first()
        organisations = Organization.objects.filter(org_type=organisation_type,district=district)
        organisation_serializer = OrganisationSerializer(organisations, many=True)
        return CustomResponse(response={'institutions': organisation_serializer.data}).get_success_response()


class PostInstitution(APIView):

    def post(self, request):
        organisation_serializer = OrganisationSerializer(data=request.data)
        if organisation_serializer.is_valid():
            organisation_serializer.save()
            return CustomResponse(response={'institution': organisation_serializer.data}).get_success_response()
        return CustomResponse(response={'institution': organisation_serializer.errors}).get_failure_response()