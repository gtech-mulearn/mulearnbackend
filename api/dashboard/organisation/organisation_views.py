import uuid
from django.db.models import Sum, Q, F, Window, Case, When
from django.db.models.functions import Rank
from rest_framework.views import APIView

from db.organization import (
    Organization,
    OrgAffiliation,
    Department,
)
from utils.permission import CustomizePermission, JWTUtils
from utils.permission import role_required
from utils.response import CustomResponse
from utils.types import RoleType, OrganizationType
from utils.types import WebHookCategory, WebHookActions
from utils.utils import CommonUtils
from utils.utils import DiscordWebhooks
from .serializers import (
    AffiliationSerializer,
    InstitutionCsvSerializer,
    DepartmentSerializer,
    InstitutionSerializer, InstitutionCreateUpdateSerializer, AffiliationCreateUpdateSerializer
)


class InstitutionPostUpdateDeleteAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def post(self, request):

        user_id = JWTUtils.fetch_user_id(request)

        serializer = InstitutionCreateUpdateSerializer(
            data=request.data,
            context={
                "user_id": user_id
            }
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
                general_message="Organisation Added Successfully"
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def put(self, request, org_code):

        user_id = JWTUtils.fetch_user_id(request)

        organization = Organization.objects.filter(
            code=org_code
        ).first()

        if organization is None:
            return CustomResponse(
                general_message="Invalid organization code"
            ).get_failure_response()

        old_title = organization.title
        old_type = organization.org_type

        serializer = InstitutionCreateUpdateSerializer(
            organization,
            data=request.data,
            context={
                "user_id": user_id
            }
        )

        if serializer.is_valid():
            serializer.save()

            if (request.data.get("title") != old_title and
                    old_type == OrganizationType.COMMUNITY.value):

                DiscordWebhooks.general_updates(
                    WebHookCategory.COMMUNITY.value,
                    WebHookActions.EDIT.value,
                    request.data.get("title"),
                    old_title,
                )

            if (request.data.get("orgType") != OrganizationType.COMMUNITY.value and
                    old_type == OrganizationType.COMMUNITY.value):

                DiscordWebhooks.general_updates(
                    WebHookCategory.COMMUNITY.value,
                    WebHookActions.DELETE.value,
                    old_title,
                )

            if (old_type != OrganizationType.COMMUNITY.value and
                    request.data.get("orgType") == OrganizationType.COMMUNITY.value):

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


class InstitutionAPI(APIView):
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


class InstitutionCsvAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, org_type):

        organization = Organization.objects.filter(
            org_type=org_type
        ).prefetch_related(
            "affiliation",
            "district__zone__state__country"
        )

        serializer = InstitutionCsvSerializer(
            organization,
            many=True
        ).data

        return CommonUtils.generate_csv(
            serializer,
            f"{org_type} data"
        )


class InstitutionDetailsAPI(APIView):
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
                'user_organization_link_org__user__wallet_user__karma'
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

        organization = organizations.filter(
            code=org_code
        ).first()

        if organization is None:
            return CustomResponse(
                general_message="Invalid organization code"
            ).get_failure_response()

        return CustomResponse(
            response=organization
        ).get_success_response()


class GetInstitutionsAPI(APIView):
    def get(self, request, org_type, district_id=None):

        if district_id:
            organisations = Organization.objects.filter(
                org_type=org_type,
                district_id=district_id
            )
        else:
            organisations = Organization.objects.filter(
                org_type=org_type
            )

        paginated_organisations = CommonUtils.get_paginated_queryset(
            organisations,
            request,
            [
                "title",
                "code"
            ]
        )

        organisation_serializer = InstitutionCsvSerializer(
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


class AffiliationGetPostUpdateDeleteAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):

        affiliation = OrgAffiliation.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(
            affiliation,
            request,
            [
                "id",
                "title"
            ])

        serializer = AffiliationSerializer(
            paginated_queryset.get("queryset"),
            many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get(
                "pagination"
            ))

    @role_required([RoleType.ADMIN.value])
    def post(self, request):

        user_id = JWTUtils.fetch_user_id(request)

        serializer = AffiliationCreateUpdateSerializer(
            data=request.data,
            context={
                "user_id": user_id,
            }
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=f"{request.data.get('title')} added successfully"
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def put(self, request, affiliation_id):

        user_id = JWTUtils.fetch_user_id(request)

        affiliation = OrgAffiliation.objects.filter(
            id=affiliation_id
        ).first()

        if affiliation is None:
            return CustomResponse(
                general_message="Invalid affiliation"
            ).get_failure_response()

        serializer = AffiliationCreateUpdateSerializer(
            affiliation,
            data=request.data,
            context={
                "user_id": user_id
            }
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=f"{affiliation.title} Edited Successfully"
            ).get_success_response()

        return CustomResponse(
            message=serializer.errors
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, affiliation_id):

        affiliation = OrgAffiliation.objects.filter(
            id=affiliation_id
        ).first()

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
    def post(self, request):
        serializer = DepartmentSerializer(
            data=request.data,
            context={
                "request": request
            })

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=f"{request.data.get('title')} created successfully"
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
                general_message=f'{department.title} updated successfully'
            ).get_success_response()

        return CustomResponse(
            response=serializer.errors
        ).get_failure_response()

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
            general_message=f'{department.id} deleted successfully'
        ).get_success_response()
