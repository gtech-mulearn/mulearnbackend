import uuid

from django.db.models import Sum
from rest_framework.views import APIView

from db.organization import Organization, UserOrganizationLink, OrgAffiliation, Country, State, District, Zone
from db.task import TotalKarma
from utils.permission import CustomizePermission, JWTUtils
from utils.permission import role_required
from utils.response import CustomResponse
from utils.types import RoleType, OrganizationType
from utils.types import WebHookCategory, WebHookActions
from utils.utils import CommonUtils
from utils.utils import DateTimeUtils
from utils.utils import DiscordWebhooks
from .serializers import AffiliationSerializer, OrganisationSerializer, PostOrganizationSerializer


class InstitutionCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def get(self, request, org_type):
        org_objs = Organization.objects.filter(org_type=org_type)
        orgs_data = OrganisationSerializer(org_objs, many=True).data
        return CommonUtils.generate_csv(orgs_data, org_type)


class InstitutionsAPI(APIView):
    def get(self, request):
        clg_orgs = Organization.objects.filter(org_type=OrganizationType.COLLEGE.value)
        cmpny_orgs = Organization.objects.filter(org_type=OrganizationType.COMPANY.value)
        cmuty_orgs = Organization.objects.filter(org_type=OrganizationType.COMMUNITY.value)

        paginated_clg_orgs = CommonUtils.get_paginated_queryset(clg_orgs, request, ['title', 'code',
                                                                                    'affiliation__title',
                                                                                    'district__name'],
                                                                {
                                                                    'title': 'title',
                                                                    'affiliation': 'affiliation',
                                                                    'district': 'district'
                                                                })
        clg_orgs_serializer = OrganisationSerializer(paginated_clg_orgs.get("queryset"), many=True)

        paginated_cmpny_orgs = CommonUtils.get_paginated_queryset(cmpny_orgs, request, ['title', 'code',
                                                                                        'district__name'],
                                                                  {
                                                                      'title': 'title',
                                                                      'district': 'district'
                                                                  })
        cmpny_orgs_serializer = OrganisationSerializer(paginated_cmpny_orgs.get("queryset"), many=True)

        paginated_cmuty_orgs = CommonUtils.get_paginated_queryset(cmuty_orgs, request, ['title', 'code'],
                                                                  {
                                                                      'title': 'title',
                                                                      'district': 'district'
                                                                  })
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

    @role_required([RoleType.ADMIN.value, ])
    def post(self, request, org_code):
        org_obj = Organization.objects.filter(code=org_code).first()
        if org_obj is None:
            return CustomResponse(general_message="Invalid Org Code").get_failure_response()
        org_type = org_obj.org_type

        if org_type == OrganizationType.COLLEGE.value:
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
            rank = next((i + 1 for i, (college_id, _) in enumerate(sorted_college_karma) if college_id == org_obj.id),
                        0)
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
        return CustomResponse().paginated_response(data=organisation_serializer.data,
                                                   pagination=paginated_organisations.get('pagination'))

    @role_required([RoleType.ADMIN.value, ])
    def post(self, request, organisation_type):
        district_name = request.data.get("district")
        district = District.objects.filter(name=district_name).first()
        organisations = Organization.objects.filter(org_type=organisation_type, district=district)
        paginated_organisations = CommonUtils.get_paginated_queryset(organisations, request, ['title', 'code'])
        organisation_serializer = OrganisationSerializer(paginated_organisations.get('queryset'), many=True)
        return CustomResponse().paginated_response(data=organisation_serializer.data,
                                                   pagination=paginated_organisations.get('pagination'))


class PostInstitutionAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(general_message="User not found").get_failure_response()

        country = request.data.get("country")
        state = request.data.get("state")
        zone = request.data.get("zone")
        district = request.data.get("district")

        country_obj = Country.objects.filter(name=country).first()
        if not country_obj:
            return CustomResponse(general_message="Country not found").get_failure_response()
        country_id = country_obj.id
        state_obj = State.objects.filter(name=state, country=country_id).first()
        if not state_obj:
            return CustomResponse(general_message="State not found").get_failure_response()
        state_id = state_obj.id
        zone_obj = Zone.objects.filter(name=zone, state=state_id).first()
        if not zone_obj:
            return CustomResponse(general_message="Zone not found").get_failure_response()
        zone_id = zone_obj.id

        district = District.objects.filter(name=district, zone=zone_id).first()
        if not district:
            return CustomResponse(general_message="District not found").get_failure_response()
        district_id = district.id

        if request.data.get("affiliation") and (request.data.get("orgType") == OrganizationType.COLLEGE.value):
            affiliation = OrgAffiliation.objects.filter(title=request.data.get("affiliation")).first()
            if not affiliation:
                return CustomResponse(general_message="Affiliation not found").get_failure_response()
            affiliation_id = affiliation.id
        else:
            affiliation_id = None

        org_id = str(uuid.uuid4())
        created_at = DateTimeUtils.get_current_utc_time()
        updated_at = DateTimeUtils.get_current_utc_time()

        values = {
            'id': org_id,
            'title': request.data.get("title"),
            'code': request.data.get("code"),
            'org_type': request.data.get("orgType"),
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
            if request.data.get("orgType") == OrganizationType.COMMUNITY.value:
                DiscordWebhooks.channelsAndCategory(
                    WebHookCategory.COMMUNITY.value,
                    WebHookActions.CREATE.value,
                    request.data.get('title')
                )
            return CustomResponse(general_message="Organisation Added Successfully").get_success_response()
        return CustomResponse(general_message=organisation_serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value, ])
    def put(self, request, org_code):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(general_message="User not found").get_failure_response()

        organisation_obj = Organization.objects.filter(code=org_code).first()
        if not organisation_obj:
            return CustomResponse(general_message="Organisation not found").get_failure_response()

        old_name = organisation_obj.title
        old_type = organisation_obj.org_type

        if request.data.get('code') and (request.data.get('code') != org_code):
            org_code_exist = Organization.objects.filter(code=request.data.get("code"))
            if org_code_exist:
                return CustomResponse(
                    general_message="Organisation with this code already exist").get_failure_response()
            else:
                request.data['code'] = request.data.get('code')

        if request.data.get("district"):
            country = request.data.get("country")
            state = request.data.get("state")
            zone = request.data.get("zone")
            district = request.data.get("district")

            country_obj = Country.objects.filter(name=country).first()
            if not country_obj:
                return CustomResponse(general_message="Country not found").get_failure_response()
            country_id = country_obj.id
            state_obj = State.objects.filter(name=state, country=country_id).first()
            if not state_obj:
                return CustomResponse(general_message="State not found").get_failure_response()
            state_id = state_obj.id
            zone_obj = Zone.objects.filter(name=zone, state=state_id).first()
            if not zone_obj:
                return CustomResponse(general_message="State not found").get_failure_response()
            zone_id = zone_obj.id
            if not zone_id:
                return CustomResponse(general_message="Zone not found").get_failure_response()

            district = District.objects.filter(name=district, zone=zone_id).first()
            if not district:
                return CustomResponse(general_message="District not found").get_failure_response()
            district_id = district.id

            request.data["district"] = district_id

        if request.data.get("orgType"):
            if request.data.get("orgType") == OrganizationType.COLLEGE.value:
                request.data["org_type"] = OrganizationType.COLLEGE.value

            else:
                request.data["org_type"] = request.data.get("orgType")
                request.data["affiliation"] = None

        if request.data.get("affiliation"):
            affiliation_name = request.data.get("affiliation")
            affiliation = OrgAffiliation.objects.filter(title=affiliation_name).first()
            if not affiliation:
                return CustomResponse(general_message="Affiliation not found").get_failure_response()
            affiliation_id = affiliation.id

            request.data["affiliation"] = affiliation_id

        if request.data.get("title"):
            request.data["title"] = request.data.get("title")

        request.data["updated_at"] = DateTimeUtils.get_current_utc_time()
        request.data["updated_by"] = user_id

        organisation_serializer = PostOrganizationSerializer(organisation_obj, data=request.data, partial=True)
        if organisation_serializer.is_valid():
            organisation_serializer.save()

            if request.data.get("title") != old_name and old_type == OrganizationType.COMMUNITY.value:
                DiscordWebhooks.channelsAndCategory(
                    WebHookCategory.COMMUNITY.value,
                    WebHookActions.EDIT.value,
                    request.data.get('title'),
                    old_name
                )

            if request.data.get("orgType"):
                if request.data.get(
                        "orgType") != OrganizationType.COMMUNITY.value and old_type == OrganizationType.COMMUNITY.value:
                    DiscordWebhooks.channelsAndCategory(
                        WebHookCategory.COMMUNITY.value,
                        WebHookActions.DELETE.value,
                        old_name
                    )

            if old_type != OrganizationType.COMMUNITY.value and request.data.get(
                    "orgType") == OrganizationType.COMMUNITY.value:
                if request.data.get("title"):
                    title = request.data.get('title')
                else:
                    title = old_name

                DiscordWebhooks.channelsAndCategory(
                    WebHookCategory.COMMUNITY.value,
                    WebHookActions.CREATE.value,
                    title
                )

            return CustomResponse(
                response={'institution': OrganisationSerializer(organisation_obj).data}).get_success_response()
        return CustomResponse(general_message=organisation_serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value, ])
    def delete(self, request, org_code):
        organisation = Organization.objects.filter(code=org_code).first()
        org_type = organisation.org_type
        if organisation:
            organisation.delete()
            if org_type == OrganizationType.COMMUNITY.value:
                DiscordWebhooks.channelsAndCategory(
                    WebHookCategory.COMMUNITY.value,
                    WebHookActions.DELETE.value,
                    organisation.title
                )
            return CustomResponse(general_message='Deleted Successfully').get_success_response()
        else:
            return CustomResponse(
                general_message=f"Org with code '{org_code}', does not exist").get_failure_response()


class AffiliationAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        affiliation = OrgAffiliation.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(affiliation, request, ['id', 'title'])
        affiliation_serializer = AffiliationSerializer(paginated_queryset.get("queryset"), many=True)
        data = {
            'affiliation': [
                {"value": data["title"],
                 "label": ' '.join(data["title"].split('_')).title()}
                for data in affiliation_serializer.data
            ],
        }

        return CustomResponse().paginated_response(data=data,
                                                   pagination=paginated_queryset.get("pagination"))

    @role_required([RoleType.ADMIN.value, ])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(general_message="User not found").get_failure_response()

        affiliation_id = str(uuid.uuid4())
        created_at = DateTimeUtils.get_current_utc_time()
        updated_at = DateTimeUtils.get_current_utc_time()
        title = request.data.get("title")
        org_exist = OrgAffiliation.objects.filter(title=title).first()
        if org_exist:
            return CustomResponse(general_message="Affiliation already exist").get_failure_response()

        values = {
            'id': affiliation_id,
            'title': title,
            'updated_by': user_id,
            'updated_at': updated_at,
            'created_by': user_id,
            'created_at': created_at,
        }

        affiliation_serializer = AffiliationSerializer(data=values)

        if affiliation_serializer.is_valid():
            affiliation_serializer.save()
            return CustomResponse(general_message="Affiliation added successfully").get_success_response()
        return CustomResponse(general_message=affiliation_serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value, ])
    def put(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(general_message="User not found").get_failure_response()

        title = request.data.get("title")
        affiliation_obj = OrgAffiliation.objects.filter(title=title).first()
        if not affiliation_obj:
            return CustomResponse(general_message="Organisation not found").get_failure_response()

        new_title = request.data.get("newTitle")

        if new_title:
            request.data["title"] = new_title

        request.data["updated_at"] = DateTimeUtils.get_current_utc_time()
        request.data["updated_by"] = user_id

        affiliation_serializer = AffiliationSerializer(affiliation_obj, data=request.data, partial=True)
        if affiliation_serializer.is_valid():
            affiliation_serializer.save()
            return CustomResponse(general_message="Affiliation edited successfully").get_success_response()
        return CustomResponse(general_message=affiliation_serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value, ])
    def delete(self, request):
        title = request.data.get("title")
        affiliation = OrgAffiliation.objects.filter(title=title).first()
        if affiliation:
            affiliation.delete()
            return CustomResponse(general_message='Deleted Successfully').get_success_response()
        else:
            return CustomResponse(
                general_message=f"Org with code {title}, does not exist").get_failure_response()


class GetInstitutionsNamesAPI(APIView):

    def get(self, request, organisation_type):
        organisations = Organization.objects.filter(org_type=organisation_type).values_list('title', flat=True)
        return CustomResponse(response=organisations).get_success_response()
