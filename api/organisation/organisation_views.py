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

        if org_id is None:
            return CustomResponse(response={'message': 'Invalid organization code'}).get_failure_response()

        org_id_list = Organization.objects.filter(org_type=org_type).values_list('id', flat=True)
        organisations = UserOrganizationLink.objects.filter(org__in=org_id_list)

        college_users = {}
        total_karma_by_college = {}

        for user_link in organisations:
            college_users.setdefault(user_link.org.id, []).append(user_link.user)

            total_karma = total_karma_by_college.get(user_link.org.id, 0)
            total_karma += TotalKarma.objects.filter(user=user_link.user).aggregate(total_karma=Sum('karma')).get(
                'total_karma', 0)
            total_karma_by_college[user_link.org.id] = total_karma

        sorted_college_karma = sorted(total_karma_by_college.items(), key=lambda x: x[1], reverse=True)
        rank = next((i + 1 for i, (college_id, _) in enumerate(sorted_college_karma) if college_id == org_id.id), 0)
        score = sorted_college_karma[rank - 1][1] if rank > 0 else 0

        return CustomResponse(response={'institution': OrganisationSerializer(org_id).data,
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

