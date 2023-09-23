import uuid

from django.db.models import Sum, Q, F, Window, Case, When
from django.db.models.functions import Rank
from rest_framework.views import APIView

from db.organization import (
    Organization,
    OrgAffiliation,
    Country,
    State,
    District,
    Zone,
    Department,
)
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
    OrganizationSerializerCreateUpdate,
    DepartmentSerializer,
    InstitutionSerializer, CollegeSerializerCreate
)


class InstitutionCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, org_type):

        organization_objects = Organization.objects.filter(
            org_type=org_type
        ).prefetch_related(
            "affiliation",
            "district__zone__state__country"
        )

        organization_data = OrganisationSerializer(
            organization_objects,
            many=True
        ).data

        return CommonUtils.generate_csv(
            organization_data,
            f"{org_type} data"
        )


class GetAllInstitutionAPI(APIView):
    def get(self, request, org_type):

        organizations = Organization.objects.filter(
            org_type=org_type
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            organizations,
            request,
            [
                "title",
                "code",
                "affiliation__title",
                "district__name",
                "district__zone__name",
                "district__zone__state__name",
                "district__zone__state__country__name"
            ],
            {
                "title": "title",
                "code": "code",
                "affiliation": "affiliation__title",
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


class GetInstitutionDetailsAPI(APIView):

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


class GetInstitutionsAPI(APIView):
    def get(self, request, organisation_type, district_id=None):

        if district_id:
            organisations = Organization.objects.filter(
                org_type=organisation_type,
                district_id=district_id
            )
        else:
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


class PostInstitutionAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        if request.data.get('affiliation') and request.data.get('org_type') == OrganizationType.COLLEGE.value:

            affiliation = OrgAffiliation.objects.filter(
                id=request.data.get('affiliation')
            ).first()

            if affiliation is None:
                organisation_serializer = OrganizationSerializerCreateUpdate(
                    data=request.data,
                    context={"request": request}
                )
            else:
                organisation_serializer = CollegeSerializerCreate(
                    data=request.data,
                    context={"request": request}
                )

            if organisation_serializer.is_valid():
                organisation_serializer.save()
                if request.data.get("org_type") == OrganizationType.COMMUNITY.value:
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
        organization = Organization.objects.filter(
            code=org_code
        ).first()

        if organization is None:
            return CustomResponse(
                general_message="Invalid organization code"
            ).get_failure_response()

        old_title = organization.title
        old_type = organization.org_type

        serializer = OrganizationSerializerCreateUpdate(
            organization,
            data=request.data,
            context={
                "request": request
            }
        )

        if serializer.is_valid():
            serializer.save()
            if (request.data.get("title") != old_title
                    and old_type == OrganizationType.COMMUNITY.value
            ):
                DiscordWebhooks.general_updates(
                    WebHookCategory.COMMUNITY.value,
                    WebHookActions.EDIT.value,
                    request.data.get("title"),
                    old_title,
                )
            if request.data.get("orgType") != OrganizationType.COMMUNITY.value and old_type == OrganizationType.COMMUNITY.value:
                DiscordWebhooks.general_updates(
                    WebHookCategory.COMMUNITY.value,
                    WebHookActions.DELETE.value,
                    old_title,
                )

            if old_type != OrganizationType.COMMUNITY.value and request.data.get("orgType") == OrganizationType.COMMUNITY.value:
                title = request.data.get("title") or old_title
                DiscordWebhooks.general_updates(
                    WebHookCategory.COMMUNITY.value,
                    WebHookActions.CREATE.value,
                    title
                )

            return CustomResponse(
                general_message="Organization Edited Successfully"
            ).get_success_response()

        return CustomResponse(
            message=serializer.errors
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

        if org_exist := OrgAffiliation.objects.filter(
                title=title
        ).first():

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

        affiliation_serializer = AffiliationSerializer(
            data=values
        )

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


        affiliation_obj = OrgAffiliation.objects.filter(
            title=title
        ).first()

        if not affiliation_obj:
            return CustomResponse(
                general_message="Organisation not found"
            ).get_failure_response()

        if new_title := request.data.get("newTitle"):

            request.data["title"] = new_title

        request.data["updated_at"] = DateTimeUtils.get_current_utc_time()
        request.data["updated_by"] = user_id

        affiliation_serializer = AffiliationSerializer(
            affiliation_obj,
            data=request.data,
            partial=True
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

        if not (affiliation := OrgAffiliation.objects.filter(
                title=title).first()):

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
        ).values_list(
            "title",
            flat=True)

        return CustomResponse(
            response=organisations
        ).get_success_response()


class DepartmentAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        serializer = DepartmentSerializer(
            data=request.data,
            context={
                "request": request
            })

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Department created successfully"
            ).get_success_response()

        return CustomResponse(
            response=serializer.errors
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def put(self, request, department_id):
        try:
            department = Department.objects.get(
                id=department_id
            )

        except Exception as e:
            return CustomResponse(
                general_message=str(e)
            ).get_failure_response()

        serializer = DepartmentSerializer(
            department,
            data=request.data,
            context={
                "request": request
            })

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message='Department updated successfully'
            ).get_success_response()

        return CustomResponse(
            response=serializer.errors
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def get(self, request, dept_id=None):

        if dept_id:
            departments = Department.objects.filter(
                id=dept_id
            )
        else:
            departments = Department.objects.all()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            departments,
            request,
            [
                "title"
            ],
            {
                "title": "title"
            })

        serializer = DepartmentSerializer(
            paginated_queryset.get(
                "queryset"
            ), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get(
                "pagination"
            ))

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, department_id):

        try:
            department = Department.objects.get(
                id=department_id
            )

        except Exception as e:
            return CustomResponse(
                general_message=str(e)
            ).get_failure_response()

        department.delete()
        return CustomResponse(
            general_message='Department deleted successfully'
        ).get_success_response()
