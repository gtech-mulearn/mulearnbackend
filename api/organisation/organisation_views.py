import uuid
from datetime import datetime

from rest_framework.views import APIView

from db.organization import Organization, District
from utils.response import CustomResponse
from .serializers import OrganisationSerializer
from . import database


db_name = "aaronchettan_new_db_2"
db_host = "localhost"
db_username = "root"
db_password = "dbsqldb"


db = database.Database(db_name, db_host, db_username, db_password)


def get_college_rank_and_karma(college_name):
    rank = []
    clg_ranks = db.get_college_rank()
    for i in clg_ranks:
        c_score = i[1]
        c_name = i[0]
        rank.append([c_name, c_score])
    rank.sort(reverse=True, key=lambda x: x[1])

    # This part will assign the rank to all the colleges in 'rank'
    c = 0
    for lo in rank:
        c += 1
        lo.append(c)

    for i in rank:
        if college_name == i[0]:
            clg_rank = i[2]  # m will receive the college rank
            clg_score = i[1]
            return clg_rank, clg_score


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

    def post(self, request):
        org_name = request.data.get("org_name")
        org_obj = Organization.objects.filter(title=org_name)

        org_ser = OrganisationSerializer(org_obj, many=True)
        clg_rank, clg_score = get_college_rank_and_karma(college_name=org_name)
        print(clg_rank, clg_score)
        # print(org_loc)
        return CustomResponse(response={'institution': org_ser.data,
                                        'rank': str(clg_rank),
                                        'score': str(clg_score)}).get_success_response()


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

    def put(self, request, org_title):
        updated_at = datetime.now()
        if request.data.get("district"):
            district_name = request.data.get("district")
            district = District.objects.filter(name=district_name).first().id
            request.data["district"] = district

        request.data["updated_at"] = updated_at

        organisation = Organization.objects.get(title=org_title)
        organisation_serializer = OrganisationSerializer(organisation, data=request.data,partial=True)
        if organisation_serializer.is_valid():
            organisation_serializer.save()
            return CustomResponse(response={'institution': organisation_serializer.data}).get_success_response()
        return CustomResponse(response={'institution': organisation_serializer.errors}).get_failure_response()

