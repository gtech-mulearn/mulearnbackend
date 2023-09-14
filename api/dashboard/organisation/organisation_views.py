import uuid

from django.db.models import Sum, Q, F, Window, Case, When, IntegerField
from django.db.models.functions import Rank
from rest_framework.views import APIView

from db.organization import (
    Organization,
    UserOrganizationLink,
    OrgAffiliation,
    Country,
    State,
    District,
    Zone,
    Department,
)
from db.task import TotalKarma
from utils.permission import CustomizePermission, JWTUtils
from utils.permission import role_required
from utils.response import CustomResponse
from utils.types import RoleType, OrganizationType
from utils.types import WebHookCategory, WebHookActions
from utils.utils import CommonUtils
from utils.utils import DateTimeUtils
from utils.utils import DiscordWebhooks
from .serializers import (
    AffiliationSerializer,
    OrganisationSerializer,
    PostOrganizationSerializer,
    DepartmentSerializer,
    InstitutionSerializer
)


class InstitutionCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, org_type):
        org_objs = Organization.objects.filter(org_type=org_type).prefetch_related(
            "affiliation", "district__zone__state__country"
        )
        orgs_data = OrganisationSerializer(org_objs, many=True).data
        return CommonUtils.generate_csv(orgs_data, org_type)


class InstitutionsAPI(APIView):
    def get(self, request):

        organizations = Organization.objects.filter(Q(
            org_type__in=[
                OrganizationType.COLLEGE.value,
                OrganizationType.COMMUNITY.value,
                OrganizationType.COMPANY.value
            ])
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            organizations,
            request,
            [
                "title",
                "code",
                "org_type"
                "affiliation__name",
                "district__name",
                "district__zone__name",
                "district__zone__state__name",
                "district__zone__state__country__name"
            ],
            {
                "title": "title",
                "code": "code",
                "org_type": "org_type",
                "affiliation": "affiliation__name",
                "district": "district__name",
                "zone": "district__zone__name",
                "state": "district__zone__state__name",
                "country": "district__zone__state__country__name"
            },
        )

        serializer = InstitutionSerializer(
            paginated_queryset.get("queryset"), many=True
        )

        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()

    #     colleges = self.get_organizations_by_type(
    #         OrganizationType.COLLEGE.value, request
    #     )
    #     companies = self.get_organizations_by_type(
    #         OrganizationType.COMPANY.value, request
    #     )
    #     communities = self.get_organizations_by_type(
    #         OrganizationType.COMMUNITY.value, request
    #     )
    #
    #     college_data = self.serialize_and_paginate(colleges)
    #     print(college_data["data"])
    #     company_data = self.serialize_and_paginate(companies)
    #     community_data = self.serialize_and_paginate(communities)
    #
    #     data = {
    #         "colleges": college_data["data"],
    #         "companies": company_data["data"],
    #         "communities": community_data["data"],
    #     }
    #
    #     pagination = {
    #         "colleges": college_data["pagination"],
    #         "companies": company_data["pagination"],
    #         "communities": community_data["pagination"],
    #     }
    #
    #     return CustomResponse().paginated_response(data=data, pagination=pagination)
    #
    # def get_organizations_by_type(self, org_type, request):
    #     organizations = Organization.objects.filter(org_type=org_type)
    #     return CommonUtils.get_paginated_queryset(
    #         organizations,
    #         request,
    #         ["title", "code", "affiliation__title", "district__name"],
    #         {
    #             "title": "title",
    #             "affiliation": "affiliation",
    #             "district": "district",
    #             "zone": "district__zone__name",
    #         },
    #     )
    #
    # def serialize_and_paginate(self, organizations):
    #     paginated_organizations = organizations.get("queryset")
    #     serializer = OrganisationSerializer(paginated_organizations, many=True)
    #     return {"data": serializer.data, "pagination": organizations.get("pagination")}

    @role_required([RoleType.ADMIN.value, ])
    def get(self, request, org_code):

        organizations = Organization.objects.all().values(
            "id",
            "title",
            "code",
            "org_type",
            affiliation_name=F("affiliation__title"),
            district_name=F("district__name"),
            zone_name=F("district__zone__name"),
            state_name=F("district__zone__state__name"),
            country_name=F("district__zone__state__country__name")
        ).annotate(
            karma=Sum(
                'user_organization_link_org__user__total_karma_user__karma'
            )).order_by(
            '-karma'
        ).annotate(
            rank=Case(
                When(
                    Q(karma__isnull=True) | Q(karma=0),
                    then=None),
                default=Window(
                    expression=Rank(),
                    order_by=F('karma').desc()
                )))

        organization = organizations.filter(code=org_code)

        return CustomResponse(response=organization).get_success_response()

        # org_obj = Organization.objects.filter(code=org_code).first()
        # if org_obj is None:
        #     return CustomResponse(
        #         general_message="Invalid Org Code"
        #     ).get_failure_response()
        # org_type = org_obj.org_type
        #
        # if org_type != OrganizationType.COLLEGE.value:
        #     return CustomResponse(
        #         response={"institution": OrganisationSerializer(org_obj).data}
        #     ).get_success_response()
        # org_id_list = Organization.objects.filter(org_type=org_type).values_list(
        #     "id", flat=True
        # )
        # organisations = UserOrganizationLink.objects.filter(org__in=org_id_list)
        # college_users = {}
        # total_karma_by_college = {}
        # for user_link in organisations:
        #     college_users.setdefault(user_link.org.id, []).append(user_link.user)
        #
        #     total_karma = total_karma_by_college.get(user_link.org.id, 0)
        #     total_karma += (
        #         TotalKarma.objects.filter(user=user_link.user)
        #         .aggregate(total_karma=Sum("karma"))
        #         .get("total_karma", 0)
        #     )
        #     total_karma_by_college[user_link.org.id] = total_karma
        #
        # sorted_college_karma = sorted(
        #     total_karma_by_college.items(), key=lambda x: x[1], reverse=True
        # )
        # rank = next(
        #     (
        #         i + 1
        #         for i, (college_id, _) in enumerate(sorted_college_karma)
        #         if college_id == org_obj.id
        #     ),
        #     0,
        # )
        # score = sorted_college_karma[rank - 1][1] if rank > 0 else 0
        #
        # return CustomResponse(
        #     response={
        #         "institution": OrganisationSerializer(org_obj).data,
        #         "rank": str(rank),
        #         "score": str(score),
        #     }
        # ).get_success_response()


class GetInstitutionsAPI(APIView):
    def get(self, request, organisation_type):

        organisations = Organization.objects.filter(
            org_type=organisation_type
        )

        paginated_organisations = CommonUtils.get_paginated_queryset(
            organisations,
            request,
            [
                "title",
                "code"
            ]
        )

        organisation_serializer = OrganisationSerializer(
            paginated_organisations.get(
                "queryset"
            ),
            many=True
        )
        return CustomResponse().paginated_response(
            data=organisation_serializer.data,
            pagination=paginated_organisations.get(
                "pagination"
            ),
        )

    @role_required([RoleType.ADMIN.value])
    def get(self, request, organisation_type, district_id):

        organisations = Organization.objects.filter(
            org_type=organisation_type,
            district_id=district_id
        )

        paginated_organisations = CommonUtils.get_paginated_queryset(
            organisations,
            request,
            [
                "title",
                "code"
            ]
        )
        organisation_serializer = OrganisationSerializer(
            paginated_organisations.get(
                "queryset"),
            many=True
        )

        return CustomResponse().paginated_response(
            data=organisation_serializer.data,
            pagination=paginated_organisations.get(
                "pagination"),
        )


class PostInstitutionAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="User not found"
            ).get_failure_response()

        country = request.data.get("country")
        state = request.data.get("state")
        zone = request.data.get("zone")
        district = request.data.get("district")

        country_obj = Country.objects.filter(name=country).first()
        if not country_obj:
            return CustomResponse(
                general_message="Country not found"
            ).get_failure_response()
        country_id = country_obj.id
        state_obj = State.objects.filter(name=state, country=country_id).first()
        if not state_obj:
            return CustomResponse(
                general_message="State not found"
            ).get_failure_response()
        state_id = state_obj.id
        zone_obj = Zone.objects.filter(name=zone, state=state_id).first()
        if not zone_obj:
            return CustomResponse(
                general_message="Zone not found"
            ).get_failure_response()
        zone_id = zone_obj.id

        district = District.objects.filter(name=district, zone=zone_id).first()
        if not district:
            return CustomResponse(
                general_message="District not found"
            ).get_failure_response()
        district_id = district.id

        if request.data.get("affiliation") and (
            request.data.get("orgType") == OrganizationType.COLLEGE.value
        ):
            if affiliation := OrgAffiliation.objects.filter(
                title=request.data.get("affiliation")
            ).first():
                affiliation_id = affiliation.id
            else:
                return CustomResponse(
                    general_message="Affiliation not found"
                ).get_failure_response()
        else:
            affiliation_id = None

        org_id = str(uuid.uuid4())
        created_at = DateTimeUtils.get_current_utc_time()
        updated_at = DateTimeUtils.get_current_utc_time()

        values = {
            "id": org_id,
            "title": request.data.get("title"),
            "code": request.data.get("code"),
            "org_type": request.data.get("orgType"),
            "affiliation": affiliation_id,
            "district": district_id,
            "updated_by": user_id,
            "updated_at": updated_at,
            "created_by": user_id,
            "created_at": created_at,
        }

        organisation_serializer = PostOrganizationSerializer(data=values)

        if organisation_serializer.is_valid():
            organisation_serializer.save()
            if request.data.get("orgType") == OrganizationType.COMMUNITY.value:
                DiscordWebhooks.general_updates(
                    WebHookCategory.COMMUNITY.value,
                    WebHookActions.CREATE.value,
                    request.data.get("title"),
                )
            return CustomResponse(
                general_message="Organisation Added Successfully"
            ).get_success_response()
        return CustomResponse(
            general_message=organisation_serializer.errors
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def put(self, request, org_code):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="User not found"
            ).get_failure_response()

        organisation_obj = Organization.objects.filter(code=org_code).first()
        if not organisation_obj:
            return CustomResponse(
                general_message="Organisation not found"
            ).get_failure_response()

        old_name = organisation_obj.title
        old_type = organisation_obj.org_type

        if request.data.get("code") and (request.data.get("code") != org_code):
            if org_code_exist := Organization.objects.filter(
                code=request.data.get("code")
            ):
                return CustomResponse(
                    general_message="Organisation with this code already exist"
                ).get_failure_response()
            else:
                request.data["code"] = request.data.get("code")

        if request.data.get("district"):
            country = request.data.get("country")
            state = request.data.get("state")
            zone = request.data.get("zone")
            district = request.data.get("district")

            country_obj = Country.objects.filter(name=country).first()
            if not country_obj:
                return CustomResponse(
                    general_message="Country not found"
                ).get_failure_response()
            country_id = country_obj.id
            state_obj = State.objects.filter(name=state, country=country_id).first()
            if not state_obj:
                return CustomResponse(
                    general_message="State not found"
                ).get_failure_response()
            state_id = state_obj.id
            zone_obj = Zone.objects.filter(name=zone, state=state_id).first()
            if not zone_obj:
                return CustomResponse(
                    general_message="State not found"
                ).get_failure_response()
            zone_id = zone_obj.id
            if not zone_id:
                return CustomResponse(
                    general_message="Zone not found"
                ).get_failure_response()

            district = District.objects.filter(name=district, zone=zone_id).first()
            if not district:
                return CustomResponse(
                    general_message="District not found"
                ).get_failure_response()
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
                return CustomResponse(
                    general_message="Affiliation not found"
                ).get_failure_response()
            affiliation_id = affiliation.id

            request.data["affiliation"] = affiliation_id

        if request.data.get("title"):
            request.data["title"] = request.data.get("title")

        request.data["updated_at"] = DateTimeUtils.get_current_utc_time()
        request.data["updated_by"] = user_id

        organisation_serializer = PostOrganizationSerializer(
            organisation_obj, data=request.data, partial=True
        )
        if organisation_serializer.is_valid():
            organisation_serializer.save()

            if (
                request.data.get("title") != old_name
                and old_type == OrganizationType.COMMUNITY.value
            ):
                DiscordWebhooks.general_updates(
                    WebHookCategory.COMMUNITY.value,
                    WebHookActions.EDIT.value,
                    request.data.get("title"),
                    old_name,
                )

            if request.data.get("orgType") and (
                                request.data.get("orgType") != OrganizationType.COMMUNITY.value
                                and old_type == OrganizationType.COMMUNITY.value
                            ):
                DiscordWebhooks.general_updates(
                    WebHookCategory.COMMUNITY.value,
                    WebHookActions.DELETE.value,
                    old_name,
                )

            if (
                old_type != OrganizationType.COMMUNITY.value
                and request.data.get("orgType") == OrganizationType.COMMUNITY.value
            ):
                title = request.data.get("title") or old_name
                DiscordWebhooks.general_updates(
                    WebHookCategory.COMMUNITY.value, WebHookActions.CREATE.value, title
                )

            return CustomResponse(
                response={"institution": OrganisationSerializer(organisation_obj).data}
            ).get_success_response()
        return CustomResponse(
            general_message=organisation_serializer.errors
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, org_code):
        if not (
            organisation := Organization.objects.filter(code=org_code).first()
        ):
            return CustomResponse(
                general_message=f"Org with code '{org_code}', does not exist"
            ).get_failure_response()
        organisation.delete()
        org_type = organisation.org_type
        if org_type == OrganizationType.COMMUNITY.value:
            DiscordWebhooks.general_updates(
                WebHookCategory.COMMUNITY.value,
                WebHookActions.DELETE.value,
                organisation.title,
            )
        return CustomResponse(
            general_message="Deleted Successfully"
        ).get_success_response()


class AffiliationAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        affiliation = OrgAffiliation.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(
            affiliation, request, ["id", "title"]
        )
        affiliation_serializer = AffiliationSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        data = {
            "affiliation": [
                {
                    "value": data["title"],
                    "label": " ".join(data["title"].split("_")).title(),
                }
                for data in affiliation_serializer.data
            ],
        }

        return CustomResponse().paginated_response(
            data=data, pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="User not found"
            ).get_failure_response()

        affiliation_id = str(uuid.uuid4())
        created_at = DateTimeUtils.get_current_utc_time()
        updated_at = DateTimeUtils.get_current_utc_time()
        title = request.data.get("title")
        if org_exist := OrgAffiliation.objects.filter(title=title).first():
            return CustomResponse(
                general_message="Affiliation already exist"
            ).get_failure_response()

        values = {
            "id": affiliation_id,
            "title": title,
            "updated_by": user_id,
            "updated_at": updated_at,
            "created_by": user_id,
            "created_at": created_at,
        }

        affiliation_serializer = AffiliationSerializer(data=values)

        if affiliation_serializer.is_valid():
            affiliation_serializer.save()
            return CustomResponse(
                general_message="Affiliation added successfully"
            ).get_success_response()
        return CustomResponse(
            general_message=affiliation_serializer.errors
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def put(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="User not found"
            ).get_failure_response()

        title = request.data.get("title")
        affiliation_obj = OrgAffiliation.objects.filter(title=title).first()
        if not affiliation_obj:
            return CustomResponse(
                general_message="Organisation not found"
            ).get_failure_response()

        if new_title := request.data.get("newTitle"):
            request.data["title"] = new_title

        request.data["updated_at"] = DateTimeUtils.get_current_utc_time()
        request.data["updated_by"] = user_id

        affiliation_serializer = AffiliationSerializer(
            affiliation_obj, data=request.data, partial=True
        )
        if affiliation_serializer.is_valid():
            affiliation_serializer.save()
            return CustomResponse(
                general_message="Affiliation edited successfully"
            ).get_success_response()
        return CustomResponse(
            general_message=affiliation_serializer.errors
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request):
        title = request.data.get("title")
        if not (affiliation := OrgAffiliation.objects.filter(title=title).first()):
            return CustomResponse(
                general_message=f"Org with code {title}, does not exist"
            ).get_failure_response()
        affiliation.delete()
        return CustomResponse(
            general_message="Deleted Successfully"
        ).get_success_response()


class GetInstitutionsNamesAPI(APIView):
    def get(self, request, organisation_type):
        organisations = Organization.objects.filter(
            org_type=organisation_type
        ).values_list("title", flat=True)
        return CustomResponse(response=organisations).get_success_response()


class DepartmentAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        serializer = DepartmentSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message="Department created successfully").get_success_response()
        return CustomResponse(response=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def put(self, request, department_id):
        try:
            department = Department.objects.get(id=department_id)
        except Department.DoesNotExist:
            return CustomResponse(general_message='Department not found').get_failure_response()

        serializer = DepartmentSerializer(department, data=request.data, context={"request": request})

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message='Department updated successfully').get_success_response()

        return CustomResponse(response=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        departments = Department.objects.all()
        serializer = DepartmentSerializer(departments, many=True)

        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, department_id):
        try:
            department = Department.objects.get(id=department_id)
        except Department.DoesNotExist:
            return CustomResponse(general_message='Department not found').get_failure_response()

        department.delete()
        return CustomResponse(general_message='Department deleted successfully').get_success_response()