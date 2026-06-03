from rest_framework.views import APIView

from db.organization import OrgAffiliation
from utils.permission import CustomizePermission, JWTUtils
from utils.permission import role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from .serializers import AffiliationCUDSerializer, AffiliationListSerializer
from drf_spectacular.utils import extend_schema






class AffiliationCRUDAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Affiliation'],
        description="Retrieve Affiliation C R U D.",
        responses={200: AffiliationListSerializer},
    )
    def get(self, request):
        affiliation = OrgAffiliation.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(
            affiliation,
            request,
            ['title', ],
            sort_fields={'title': 'title', }

        )

        serializer = AffiliationListSerializer(
            paginated_queryset.get("queryset"),
            many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get(
                "pagination"
            )
        )

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Affiliation'],
        description="Create Affiliation C R U D.",
        request=AffiliationCUDSerializer,
        responses={200: AffiliationListSerializer},
    )
    def post(self, request):

        user_id = JWTUtils.fetch_user_id(request)

        serializer = AffiliationCUDSerializer(
            data=request.data,
            context={
                "user_id": user_id,
            }
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=f"{request.data.get('title')} Affiliation created successfully",
                response=serializer.data
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors,
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Affiliation'],
        description="Update Affiliation C R U D.",
        responses={200: AffiliationCUDSerializer},
    )
    def put(self, request, affiliation_id):

        user_id = JWTUtils.fetch_user_id(request)

        affiliation = OrgAffiliation.objects.filter(
            id=affiliation_id
        ).first()

        if affiliation is None:
            return CustomResponse(
                general_message="Invalid affiliation id"
            ).get_failure_response()

        serializer = AffiliationCUDSerializer(
            affiliation,
            data=request.data,
            context={"user_id": user_id}
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
    @extend_schema(tags=['Dashboard - Affiliation'], description="Delete Affiliation C R U D.",
        responses={200: AffiliationListSerializer},
    )
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
