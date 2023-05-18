import uuid
from datetime import datetime

from django.db.models import Sum
from rest_framework.views import APIView

from db.organization import Organization, District, UserOrganizationLink, OrgAffiliation
from db.task import TotalKarma
from utils.permission import CustomizePermission, JWTUtils
from utils.permission import RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from .serializers import OrganisationSerializer, PostOrganizationSerializer
from utils.utils import CommonUtils


class Institutions(APIView):
    authentication_classes = [CustomizePermission]
    @RoleRequired(roles=[RoleType.ADMIN, ])
    def get(self, request):
        clg_orgs = Organization.objects.filter(org_type="College")
        cmpny_orgs = Organization.objects.filter(org_type="Company")
        cmuty_orgs = Organization.objects.filter(org_type="Community")

        paginated_clg_orgs = CommonUtils.paginate_queryset(clg_orgs, request,
                                                                ['id', 'name'])
        clg_orgs_serializer = OrganisationSerializer(paginated_clg_orgs, many=True)

        paginated_cmpny_orgs = CommonUtils.paginate_queryset(cmpny_orgs, request,
                                                                ['id', 'name'])
        cmpny_orgs_serializer = OrganisationSerializer(paginated_cmpny_orgs, many=True)

        paginated_cmuty_orgs = CommonUtils.paginate_queryset(cmuty_orgs, request,
                                                                ['id', 'name'])
        cmuty_orgs_serializer = OrganisationSerializer(paginated_cmuty_orgs, many=True)

        return CustomResponse(response={'colleges': clg_orgs_serializer.data,
                                        'companies': cmpny_orgs_serializer.data,
                                        'communities': cmuty_orgs_serializer.data}).get_success_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
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
    authentication_classes = [CustomizePermission]

    def get(self, request, organisation_type):
        organisations = Organization.objects.filter(org_type=organisation_type)
        paginated_organisations = CommonUtils.paginate_queryset(organisations, request,
                                                                ['id', 'name'])
        organisation_serializer = OrganisationSerializer(paginated_organisations, many=True)
        return CustomResponse(response={'institutions': organisation_serializer.data}).get_success_response()

    def post(self, request, organisation_type):
        district_name = request.data.get("district_name")
        district = District.objects.filter(name=district_name).first()
        organisations = Organization.objects.filter(org_type=organisation_type, district=district)
        paginated_organisations = CommonUtils.paginate_queryset(organisations, request,
                                                                ['id', 'name'])
        organisation_serializer = OrganisationSerializer(paginated_organisations, many=True)
        return CustomResponse(response={'institutions': organisation_serializer.data}).get_success_response()


class PostInstitution(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def post(self, request):
        org_id = str(uuid.uuid4())
        created_at = datetime.now()
        updated_at = datetime.now()
        district_name = request.data.get("district")
        affiliation_name = request.data.get("affiliation")
        district = District.objects.filter(name=district_name).first().id
        affiliation = OrgAffiliation.objects.filter(title=affiliation_name).first().id

        values = {
            'id': org_id,
            'title': request.data.get("title"),
            'code': request.data.get("code"),
            'org_type': request.data.get("org_type"),
            'affiliation': affiliation,
            'district': district,
            'updated_by': JWTUtils.fetch_user_id(request),
            'updated_at': updated_at,
            'created_by': JWTUtils.fetch_user_id(request),
            'created_at': created_at,
        }

        organisation_serializer = PostOrganizationSerializer(data=values)
        if organisation_serializer.is_valid():
            organisation_serializer.save()
            return CustomResponse(response={'institution': organisation_serializer.data}).get_success_response()
        return CustomResponse(response={'institution': organisation_serializer.errors}).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def put(self, request, org_code):
        updated_at = datetime.now()
        if request.data.get("district"):
            district_name = request.data.get("district")
            district = District.objects.filter(name=district_name).first().id
            request.data["district"] = district

        request.data["updated_at"] = updated_at
        request.data["updated_by"] = JWTUtils.fetch_user_id(request)

        # The org type is checked because if it is not college -> affiliation will not be passed in request.data,
        # then checking for affiliation in db will return None -> results in error
        if request.data.get("org_type") == "College":
            org_affiliation_name = request.data.get("affiliation")
            org_affiliation = OrgAffiliation.objects.filter(title=org_affiliation_name).first().id
            request.data["affiliation"] = org_affiliation

        organisation = Organization.objects.get(code=org_code)
        organisation_serializer = PostOrganizationSerializer(organisation, data=request.data, partial=True)
        if organisation_serializer.is_valid():
            organisation_serializer.save()
            return CustomResponse(response={'institution': organisation_serializer.data}).get_success_response()
        return CustomResponse(response={'institution': organisation_serializer.errors}).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def delete(self, request, org_code):
        organisation = Organization.objects.get(code=org_code)
        organisation.delete()
        return CustomResponse(response={'message': 'Deleted Successfully'}).get_success_response()
