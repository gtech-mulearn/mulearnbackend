from rest_framework.views import APIView

from organization.models import Organization
from .serializers import OrganisationSerializer
from utils.utils_views import CustomResponse

class GetInstitutions(APIView):

    def get(self, request,organisation_type):
        orgainisations = Organization.objects.filter(org_type=organisation_type)
        orgainsation_serializer = OrganisationSerializer(orgainisations, many=True)
        return CustomResponse(response={'institutions': orgainsation_serializer.data}).get_success_response()
