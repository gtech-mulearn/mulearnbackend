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
