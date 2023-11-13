from django.db.models import F, Prefetch, Sum
from rest_framework.views import APIView

from db.organization import (
    Department,
    OrgAffiliation,
    Organization,
    UserOrganizationLink,
)
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType, WebHookActions, WebHookCategory
from utils.utils import CommonUtils, DiscordWebhooks

from .serializers import (
    AffiliationCreateUpdateSerializer,
    AffiliationSerializer,
    DepartmentSerializer,
    InstitutionCreateUpdateSerializer,
    InstitutionSerializer,
    InstitutionPrefillSerializer,
    OrganizationMergerSerializer, OrganizationKarmaTypeGetPostPatchDeleteSerializer,
    OrganizationKarmaLogGetPostPatchDeleteSerializer,
)


class InstitutionPostUpdateDeleteAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        serializer = InstitutionCreateUpdateSerializer(
            data=request.data, context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()

            if request.data.get("org_type") == OrganizationType.COMMUNITY.value:
                DiscordWebhooks.general_updates(
                    WebHookCategory.COMMUNITY.value,
                    WebHookActions.CREATE.value,
                    request.data.get("title"),
                )

            return CustomResponse(
                general_message="Organisation added successfully"
            ).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def put(self, request, org_code):
        user_id = JWTUtils.fetch_user_id(request)

        organization = Organization.objects.filter(code=org_code).first()

        if organization is None:
            return CustomResponse(
                general_message="Invalid organization code"
            ).get_failure_response()

        old_title = organization.title
        old_type = organization.org_type

        serializer = InstitutionCreateUpdateSerializer(
            organization, data=request.data, context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()

            if (
                request.data.get("title") != old_title
                and old_type == OrganizationType.COMMUNITY.value
            ):
                DiscordWebhooks.general_updates(
                    WebHookCategory.COMMUNITY.value,
                    WebHookActions.EDIT.value,
                    request.data.get("title"),
                    old_title,
                )

            if (
                request.data.get("orgType") != OrganizationType.COMMUNITY.value
                and old_type == OrganizationType.COMMUNITY.value
            ):
                DiscordWebhooks.general_updates(
                    WebHookCategory.COMMUNITY.value,
                    WebHookActions.DELETE.value,
                    old_title,
                )

            if (
                old_type != OrganizationType.COMMUNITY.value
                and request.data.get("orgType") == OrganizationType.COMMUNITY.value
            ):
                title = request.data.get("title") or old_title
                DiscordWebhooks.general_updates(
                    WebHookCategory.COMMUNITY.value, WebHookActions.CREATE.value, title
                )

            return CustomResponse(
                general_message="Organization edited successfully"
            ).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, org_code):
        if not (organisation := Organization.objects.filter(code=org_code).first()):
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
            general_message="Organization deleted successfully"
        ).get_success_response()


class InstitutionAPI(APIView):
    def get(self, request, org_type, district_id=None):
        if district_id:
            organisations = Organization.objects.filter(
                org_type=org_type, district_id=district_id
            )
        else:
            organisations = Organization.objects.filter(org_type=org_type)

        org_queryset = organisations.select_related(
            "affiliation",
            # 'district',
            # "district__zone__state__country",
            # "district__zone__state",
            # "district__zone",
            # "district",
        ).prefetch_related(
            Prefetch(
                "user_organization_link_org",
                queryset=UserOrganizationLink.objects.filter(
                    verified=True
                ).select_related("user"),
            )
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            org_queryset,
            request,
            [
                "title",
                "code",
                "affiliation__title",
                "district__name",
                "district__zone__name",
                "district__zone__state__name",
                "district__zone__state__country__name",
            ],
            {
                "title": "title",
                "code": "code",
                "affiliation": "affiliation__title",
                "district": "district__name",
                "zone": "district__zone__name",
                "state": "district__zone__state__name",
                "country": "district__zone__state__country__name",
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


class InstitutionCSVAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, org_type):
        organizations = (
            Organization.objects.filter(org_type=org_type)
            .select_related(
                "affiliation",
                # "district__zone__state__country",
                # "district__zone__state",
                # "district__zone",
                # "district",
            )
            .prefetch_related(
                Prefetch(
                    "user_organization_link_org",
                    queryset=UserOrganizationLink.objects.filter(
                        verified=True
                    ).select_related("user"),
                )
            )
        )

        serializer = InstitutionSerializer(organizations, many=True).data

        return CommonUtils.generate_csv(serializer, f"{org_type} data")


class InstitutionDetailsAPI(APIView):
    @role_required(
        [
            RoleType.ADMIN.value,
        ]
    )
    def get(self, request, org_code):
        organization = (
            Organization.objects.filter(code=org_code)
            .values(
                "id",
                "title",
                "code",
                affiliation_uuid=F("affiliation__id"),
                affiliation_name=F("affiliation__title"),
                district_uuid=F("district__id"),
                district_name=F("district__name"),
                zone_uuid=F("district__zone__id"),
                zone_name=F("district__zone__name"),
                state_uuid=F("district__zone__state__id"),
                state_name=F("district__zone__state__name"),
                country_uuid=F("district__zone__state__country__id"),
                country_name=F("district__zone__state__country__name"),
            )
            .annotate(karma=Sum("user_organization_link_org__user__wallet_user__karma"))
            .order_by("-karma")
        )

        return CustomResponse(response=organization).get_success_response()


class GetInstitutionsAPI(APIView):
    def get(self, request, org_type, district_id=None):
        if district_id:
            organisations = Organization.objects.filter(
                org_type=org_type, district_id=district_id
            )
        else:
            organisations = Organization.objects.filter(org_type=org_type)

        paginated_organisations = CommonUtils.get_paginated_queryset(
            organisations, request, ["title", "code"]
        )

        organisation_serializer = InstitutionSerializer(
            paginated_organisations.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=organisation_serializer.data,
            pagination=paginated_organisations.get("pagination"),
        )


class AffiliationGetPostUpdateDeleteAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        affiliation = OrgAffiliation.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(
            affiliation, request, ["id", "title"]
        )
        serializer = AffiliationSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        serializer = AffiliationCreateUpdateSerializer(
            data=request.data,
            context={
                "user_id": user_id,
            },
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=f"{request.data.get('title')} added successfully"
            ).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def put(self, request, affiliation_id):
        user_id = JWTUtils.fetch_user_id(request)

        affiliation = OrgAffiliation.objects.filter(id=affiliation_id).first()

        if affiliation is None:
            return CustomResponse(
                general_message="Invalid affiliation"
            ).get_failure_response()

        serializer = AffiliationCreateUpdateSerializer(
            affiliation, data=request.data, context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=f"{affiliation.title} Edited Successfully"
            ).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, affiliation_id):
        affiliation = OrgAffiliation.objects.filter(id=affiliation_id).first()

        if affiliation is None:
            return CustomResponse(
                general_message="Invalid affiliation id"
            ).get_failure_response()

        affiliation.delete()

        return CustomResponse(
            general_message=f"{affiliation.title} Deleted Successfully"
        ).get_success_response()


class DepartmentAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, dept_id=None):
        if dept_id:
            departments = Department.objects.filter(id=dept_id)
        else:
            departments = Department.objects.all()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            departments, request, ["title"], {"title": "title"}
        )

        serializer = DepartmentSerializer(paginated_queryset.get("queryset"), many=True)

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        serializer = DepartmentSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=f"{request.data.get('title')} created successfully"
            ).get_success_response()

        return CustomResponse(response=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def put(self, request, department_id):
        department = Department.objects.get(id=department_id)

        serializer = DepartmentSerializer(
            department, data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=f"{department.title} updated successfully"
            ).get_success_response()

        return CustomResponse(response=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, department_id):
        department = Department.objects.get(id=department_id)

        department.delete()
        return CustomResponse(
            general_message=f"{department.title} deleted successfully"
        ).get_success_response()


class AffiliationListAPI(APIView):
    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        affiliation = OrgAffiliation.objects.all().values("id", "title")

        return CustomResponse(response=affiliation).get_success_response()


class InstitutionPrefillAPI(APIView):
    @role_required(
        [
            RoleType.ADMIN.value,
        ]
    )
    def get(self, request, org_code):
        organization = Organization.objects.filter(code=org_code).first()

        serializer = InstitutionPrefillSerializer(organization, many=False).data

        return CustomResponse(response=serializer).get_success_response()


class OrganizationMergerView(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, organisation_id):
        try:
            destination = Organization.objects.get(pk=organisation_id)
            serializer = OrganizationMergerSerializer(destination, data=request.data)
            if not serializer.is_valid():
                return CustomResponse(
                    general_message=serializer.errors
                ).get_failure_response()

            return CustomResponse(response=serializer.data).get_success_response()

        except Organization.DoesNotExist:
            return CustomResponse(
                general_message="An organization with the given id doesn't exist"
            ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, organisation_id):
        try:
            destination = Organization.objects.get(pk=organisation_id)
            serializer = OrganizationMergerSerializer(destination, data=request.data)
            if not serializer.is_valid():
                return CustomResponse(
                    general_message=serializer.errors
                ).get_failure_response()
            serializer.save()

            return CustomResponse(
                general_message=f"Organizations merged successfully into {destination.title}."
            ).get_success_response()

        except Organization.DoesNotExist:
            return CustomResponse(
                general_message="An organization with the given id doesn't exist"
            ).get_failure_response()


class OrganizationKarmaTypeGetPostPatchDeleteAPI(APIView):
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        serializer = OrganizationKarmaTypeGetPostPatchDeleteSerializer(
            data=request.data,
            context={
                'user_id': user_id
            }
        )
        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                "Organization karma type created successfully"
            ).get_success_response()

        return CustomResponse(
            serializer.errors
        ).get_failure_response()


class OrganizationKarmaLogGetPostPatchDeleteAPI(APIView):
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        serializer = OrganizationKarmaLogGetPostPatchDeleteSerializer(
            data=request.data,
            context={
                'user_id': user_id
            }
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                "Organization karma Log created successfully"
            ).get_success_response()

        return CustomResponse(
            serializer.errors
        ).get_failure_response()
