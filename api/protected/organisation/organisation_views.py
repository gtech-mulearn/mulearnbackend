from decouple import config
from rest_framework.views import APIView

from db.organization import Organization, District
from utils.response import CustomResponse
from .serializer import OrganisationSerializer


class GetInstitutions(APIView):

    def get(self, request, organisation_type):
        protection_key = request.headers.get("protectionKey")
        if protection_key is None:
            return CustomResponse(general_message="Invalid Key").get_failure_response()

        if not protection_key == config('PROTECTED_API_KEY'):
            return CustomResponse(general_message="Invalid Key").get_failure_response()

        organisations = Organization.objects.filter(org_type=organisation_type)
        organisation_serializer = OrganisationSerializer(organisations, many=True)
        return CustomResponse(response={'institutions': organisation_serializer.data}).get_success_response()

    def post(self, request, organisation_type):
        protection_key = request.headers.get("protectionKey")
        if protection_key is None:
            return CustomResponse(general_message="Invalid Key").get_failure_response()

        if not protection_key == config('PROTECTED_API_KEY'):
            return CustomResponse(general_message="Invalid Key").get_failure_response()

        district_name = request.data.get("district")
        district = District.objects.filter(name=district_name).first()
        organisations = Organization.objects.filter(org_type=organisation_type, district=district)
        organisation_serializer = OrganisationSerializer(organisations, many=True)
        return CustomResponse(response={'institutions': organisation_serializer.data}).get_success_response()
