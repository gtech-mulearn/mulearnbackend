import uuid
from datetime import datetime

from django.db.models import Sum
from rest_framework.views import APIView

from db.organization import Organization, UserOrganizationLink, OrgAffiliation, Country, State, District, Zone
from db.task import TotalKarma
from utils.permission import CustomizePermission, JWTUtils
from utils.permission import RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from .serializers import OrganisationSerializer, PostOrganizationSerializer
from utils.utils import CommonUtils


class InstitutionsAPI(APIView):
    def get(self, request):
        clg_orgs = Organization.objects.filter(org_type="College")
        cmpny_orgs = Organization.objects.filter(org_type="Company")
        cmuty_orgs = Organization.objects.filter(org_type="Community")

        paginated_clg_orgs = CommonUtils.get_paginated_queryset(clg_orgs, request, ['name', 'code'])
        clg_orgs_serializer = OrganisationSerializer(paginated_clg_orgs.get("queryset"), many=True)

        paginated_cmpny_orgs = CommonUtils.get_paginated_queryset(cmpny_orgs, request, ['name', 'code'])
        cmpny_orgs_serializer = OrganisationSerializer(paginated_cmpny_orgs.get("queryset"), many=True)

        paginated_cmuty_orgs = CommonUtils.get_paginated_queryset(cmuty_orgs, request, ['name', 'code'])
        cmuty_orgs_serializer = OrganisationSerializer(paginated_cmuty_orgs.get("queryset"), many=True)

        data = {
            'colleges': clg_orgs_serializer.data,
            'companies': cmpny_orgs_serializer.data,
            'communities': cmuty_orgs_serializer.data
        }

        pagination = {
            'colleges': paginated_clg_orgs.get("pagination"),
            'companies': paginated_cmpny_orgs.get("pagination"),
            'communities': paginated_cmuty_orgs.get("pagination")
        }

        return CustomResponse().paginated_response(data=data, pagination=pagination)

    def post(self, request, org_code):
        org_obj = Organization.objects.filter(code=org_code).first()
        if org_obj is None:
            return CustomResponse(general_message=["Invalid Org Code"]).get_failure_response()
        org_type = org_obj.org_type

        if org_type == "College":
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
            rank = next((i + 1 for i, (college_id, _) in enumerate(sorted_college_karma) if college_id == org_obj.id), 0)
            score = sorted_college_karma[rank - 1][1] if rank > 0 else 0

            return CustomResponse(response={'institution': OrganisationSerializer(org_obj).data,
                                            'rank': str(rank),
                                            'score': str(score)}).get_success_response()
        else:
            return CustomResponse(response={'institution': OrganisationSerializer(org_obj).data}).get_success_response()


class GetInstitutionsAPI(APIView):
    def get(self, request, organisation_type):
        organisations = Organization.objects.filter(org_type=organisation_type)
        paginated_organisations = CommonUtils.get_paginated_queryset(organisations, request, ['title', 'code'])

        organisation_serializer = OrganisationSerializer(paginated_organisations.get('queryset'), many=True)
        # organisation_serializer = OrganisationSerializer(organisations, many=True)
        return CustomResponse().paginated_response(data=organisation_serializer.data, pagination=paginated_organisations.get('pagination'))

    def post(self, request, organisation_type):
        district_name = request.data.get("district")
        district = District.objects.filter(name=district_name).first()
        organisations = Organization.objects.filter(org_type=organisation_type, district=district)
        paginated_organisations = CommonUtils.get_paginated_queryset(organisations, request, ['title', 'code'])
        organisation_serializer = OrganisationSerializer(paginated_organisations.get('queryset'), many=True)
        return CustomResponse().paginated_response(data=organisation_serializer.data, pagination=paginated_organisations.get('pagination'))


class PostInstitutionAPI(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(general_message=["User not found"]).get_failure_response()

        country = request.data.get("country")
        state = request.data.get("state")
        zone = request.data.get("zone")
        district = request.data.get("district")

        country_obj = Country.objects.filter(name=country).first()
        if not country_obj:
            return CustomResponse(general_message=["Country not found"]).get_failure_response()
        country_id = country_obj.id
        state_obj = State.objects.filter(name=state, country=country_id).first()
        if not state_obj:
            return CustomResponse(general_message=["State not found"]).get_failure_response()
        state_id = state_obj.id
        zone_obj = Zone.objects.filter(name=zone, state=state_id).first()
        if not zone_obj:
            return CustomResponse(general_message=["State not found"]).get_failure_response()
        zone_id = zone_obj.id
        if not zone_id:
            return CustomResponse(general_message=["Zone not found"]).get_failure_response()

        district = District.objects.filter(name=district, zone=zone_id).first()
        if not district:
            return CustomResponse(general_message=["District not found"]).get_failure_response()
        district_id = district.id

        if request.data.get("affiliation"):
            affiliation = OrgAffiliation.objects.filter(title=request.data.get("affiliation")).first()
            if not affiliation:
                return CustomResponse(general_message=["Affiliation not found"]).get_failure_response()
            affiliation_id = affiliation.id
        else:
            affiliation_id = None

        org_id = str(uuid.uuid4())
        created_at = datetime.now()
        updated_at = datetime.now()


        values = {
            'id': org_id,
            'title': request.data.get("title"),
            'code': request.data.get("code"),
            'org_type': request.data.get("org_type"),
            'affiliation': affiliation_id,
            'district': district_id,
            'updated_by': user_id,
            'updated_at': updated_at,
            'created_by': user_id,
            'created_at': created_at,
        }

        organisation_serializer = PostOrganizationSerializer(data=values)
        if organisation_serializer.is_valid():
            organisation_serializer.save()
            org_obj = Organization.objects.filter(code=values["code"]).first()
            return CustomResponse(response={'institution': OrganisationSerializer(org_obj).data}).get_success_response()
        return CustomResponse(general_message=[organisation_serializer.errors]).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def put(self, request, org_code):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(general_message=["User not found"]).get_failure_response()

        organisation_obj = Organization.objects.filter(code=org_code).first()
        if not organisation_obj:
            return CustomResponse(general_message=["Organisation not found"]).get_failure_response()

        if request.data.get('code'):
            org_code_exist = Organization.objects.filter(code=request.data.get("code"))
            if org_code_exist:
                return CustomResponse(general_message=["Organisation with this code already exist"]).get_failure_response()
            else:
                request.data['code'] = request.data.get('code')

        if request.data.get("district"):
            country = request.data.get("country")
            state = request.data.get("state")
            zone = request.data.get("zone")
            district = request.data.get("district")

            country_obj = Country.objects.filter(name=country).first()
            if not country_obj:
                return CustomResponse(general_message=["Country not found"]).get_failure_response()
            country_id = country_obj.id
            state_obj = State.objects.filter(name=state, country=country_id).first()
            if not state_obj:
                return CustomResponse(general_message=["State not found"]).get_failure_response()
            state_id = state_obj.id
            zone_obj = Zone.objects.filter(name=zone, state=state_id).first()
            if not zone_obj:
                return CustomResponse(general_message=["State not found"]).get_failure_response()
            zone_id = zone_obj.id
            if not zone_id:
                return CustomResponse(general_message=["Zone not found"]).get_failure_response()

            district = District.objects.filter(name=district, zone=zone_id).first()
            if not district:
                return CustomResponse(general_message=["District not found"]).get_failure_response()
            district_id = district.id

            request.data["district"] = district_id

        if request.data.get("org_type"):
            if request.data.get("org_type") == "College":
                request.data["org_type"] = "College"

            else:
                request.data["org_type"] = request.data.get("org_type")
                request.data["affiliation"] = None

        if request.data.get("affiliation"):
            affiliation_name = request.data.get("affiliation")
            affiliation = OrgAffiliation.objects.filter(title=affiliation_name).first()
            if not affiliation:
                return CustomResponse(general_message=["Affiliation not found"]).get_failure_response()
            affiliation_id = affiliation.id

            request.data["affiliation"] = affiliation_id

        if request.data.get("title"):
            request.data["title"] = request.data.get("title")

        request.data["updated_at"] = datetime.now()
        request.data["updated_by"] = user_id



        organisation_serializer = PostOrganizationSerializer(organisation_obj, data=request.data, partial=True)
        if organisation_serializer.is_valid():
            organisation_serializer.save()
            return CustomResponse(response={'institution': OrganisationSerializer(organisation_obj).data}).get_success_response()
        return CustomResponse(general_message=[organisation_serializer.errors]).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def delete(self, request, org_code):
        organisation = Organization.objects.filter(code=org_code).first()
        if organisation:
            organisation.delete()
            return CustomResponse(response={'Success': 'Deleted Successfully'}).get_success_response()
        else:
            return CustomResponse(general_message=[f"Org with code '{org_code}', does not exist"]).get_failure_response()
