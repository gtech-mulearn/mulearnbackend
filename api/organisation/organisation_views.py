import uuid
from datetime import datetime

from django.db.models import Sum
from rest_framework.views import APIView

from db.organization import Organization, District, UserOrganizationLink
from db.task import TotalKarma

from utils.response import CustomResponse
from .serializers import OrganisationSerializer



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

    def post(self, request, org_code):
        org_type = request.data.get("org_type")
        org_id = Organization.objects.filter(code=org_code).first()
        org_ser = OrganisationSerializer(org_id)

        if org_id is None:
            return CustomResponse(response={'message': 'Invalid organization code'}).get_failure_response()

        org_id_list = Organization.objects.filter(org_type=org_type).values_list('id', flat=True)
        organisations = [org_id for org_id in org_id_list]

        college_users = {}
        for org in organisations:
            users = UserOrganizationLink.objects.filter(org=org)
            college_users[org] = [user.user for user in users]

        college_karma = {}
        for clg in college_users:
            total_karma = TotalKarma.objects.filter(user__in=college_users[clg]).aggregate(total_karma=Sum('karma'))
            if total_karma['total_karma'] is None:
                total_karma['total_karma'] = 0
            college_karma[clg] = total_karma

        sorted_college_karma = sorted(college_karma.items(), key=lambda x: x[1]['total_karma'], reverse=True)
        index = 0
        for i in range(len(sorted_college_karma)):
            if sorted_college_karma[i][0] == org_id.id:
                index = i
                break

        rank = index + 1
        score = sorted_college_karma[index][1]['total_karma']

        return CustomResponse(response={'institution': org_ser.data,
                                        'rank': str(rank),
                                        'score': str(score)}).get_success_response()


class GetInstitutions(APIView):
    def get(self, request, organisation_type):
        organisations = Organization.objects.filter(org_type=organisation_type)
        organisation_serializer = OrganisationSerializer(organisations, many=True)
        return CustomResponse(response={'institutions': organisation_serializer.data}).get_success_response()

    def post(self, request, organisation_type):
        district_name = request.data.get("district")
        district = District.objects.filter(name=district_name).first()
        organisations = Organization.objects.filter(org_type=organisation_type, district=district)
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

    def put(self, request, org_code):
        updated_at = datetime.now()
        if request.data.get("district"):
            district_name = request.data.get("district")
            district = District.objects.filter(name=district_name).first().id
            request.data["district"] = district

        request.data["updated_at"] = updated_at

        organisation = Organization.objects.get(code=org_code)
        organisation_serializer = OrganisationSerializer(organisation, data=request.data, partial=True)
        if organisation_serializer.is_valid():
            organisation_serializer.save()
            return CustomResponse(response={'institution': organisation_serializer.data}).get_success_response()
        return CustomResponse(response={'institution': organisation_serializer.errors}).get_failure_response()

    def delete(self, request, org_code):
        organisation = Organization.objects.get(code=org_code)
        organisation.delete()
        return CustomResponse(response={'message': 'Deleted Successfully'}).get_success_response()

