import uuid
from datetime import datetime

from rest_framework.views import APIView

from organization.models import Organization, District
from .serializers import OrganisationSerializer
from utils.utils_views import CustomResponse


class Institutions(APIView):
    def get(self, request):
        clg_orgs = Organization.objects.filter(org_type="College")
        cmpny_orgs = Organization.objects.filter(org_type="Company")
        cmuty_orgs = Organization.objects.filter(org_type="Community")

        clg_orgs_serializer = OrganisationSerializer(clg_orgs, many=True)
        cmpny_orgs_serializer = OrganisationSerializer(cmpny_orgs, many=True)
        cmuty_orgs_serializer = OrganisationSerializer(cmuty_orgs, many=True)

        return CustomResponse(response={'colleges': clg_orgs_serializer.data,
                                        'companies': cmpny_orgs_serializer.data,
                                        'communities': cmuty_orgs_serializer.data}).get_success_response()


class GetInstitutions(APIView):
    def get(self, request, organisation_type):
        organisations = Organization.objects.filter(org_type=organisation_type)
        print(organisations)
        print("###################")
        organisation_serializer = OrganisationSerializer(organisations, many=True)
        print(organisation_serializer)
        print(type(organisation_serializer))
        print("###################")

        print(organisation_serializer.data)
        print(type(organisation_serializer.data))
        print("###################")

        return CustomResponse(response={'institutions': organisation_serializer.data}).get_success_response()


    def post(self, request, organisation_type):
        district_name = request.data.get("district")
        district = District.objects.filter(name=district_name).first()
        organisations = Organization.objects.filter(org_type=organisation_type,district=district)
        organisation_serializer = OrganisationSerializer(organisations, many=True)
        return CustomResponse(response={'institutions': organisation_serializer.data}).get_success_response()



class PostInstitution(APIView):

    def post(self, request):
        org_id = str(uuid.uuid4())
        created_at = datetime.now()
        updated_at = datetime.now()
        district_name = request.data.get("district")
        district = District.objects.filter(name=district_name).first().id

        values = {
            'id': org_id,
            'title': request.data.get("title"),
            'code': request.data.get("code"),
            'org_type': request.data.get("org_type"),
            'district': district,
            'affiliation': request.data.get("affiliation"),
            'updated_by': request.data.get("updated_by"),
            'updated_at': updated_at,
            'created_by': request.data.get("created_by"),
            'created_at': created_at,
        }

        organisation_serializer = OrganisationSerializer(data=values)
        if organisation_serializer.is_valid():
            organisation_serializer.save()
            return CustomResponse(response={'institution': organisation_serializer.data}).get_success_response()
        return CustomResponse(response={'institution': organisation_serializer.errors}).get_failure_response()
