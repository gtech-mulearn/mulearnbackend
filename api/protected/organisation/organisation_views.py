from decouple import config
from rest_framework.views import APIView

from db.organization import Organization, District
from utils.response import CustomResponse
from .serializer import OrganisationSerializer, InstitutesRetrivalSerializer
from drf_spectacular.utils import extend_schema


class GetInstitutionsAPI(APIView):

    @extend_schema(
        tags=['Protected - Organisation'],
        description="Retrieve Get Institutions.",
        responses={200: OrganisationSerializer},
    )
    def get(self, request, organisation_type, district_name):
        protection_key = request.headers.get("protectionKey")
        if not protection_key or not protection_key == config('PROTECTED_API_KEY'):
            return CustomResponse(general_message="Invalid Key").get_failure_response()

        district = District.objects.filter(name=district_name).first()

        organisations = Organization.objects.filter(org_type=organisation_type, district=district)
        organisation_serializer = OrganisationSerializer(organisations, many=True)
        return CustomResponse(response={'institutions': organisation_serializer.data}).get_success_response()


class RetrieveInstitutesAPI(APIView):
    @extend_schema(
        tags=['Protected - Organisation'],
        description="Retrieve Retrieve Institutes.",
        responses={200: InstitutesRetrivalSerializer},
    )
    def get(self, request, district_name):
        district = District.objects.filter(name=district_name).first()
        organisations = Organization.objects.filter(org_type__in=["School", "College"], district=district)
        serializer = InstitutesRetrivalSerializer(organisations, many=True)
        return CustomResponse(response=serializer.data).get_success_response()
