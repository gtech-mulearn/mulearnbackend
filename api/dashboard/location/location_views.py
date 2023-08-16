import uuid

from rest_framework.views import APIView

from db.organization import Country, District, State, Zone
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils

from .location_serializer import CountrySerializer


class CountryDataAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, country_id=None):
        try:
            if country_id:
                countries = Country.objects.filter(id=country_id)
            else:
                countries = Country.objects.all()

            paginated_queryset = CommonUtils.get_paginated_queryset(
                countries, request, ["name"], {"name": "name"}
            )

            serializer = CountrySerializer(
                paginated_queryset.get("queryset"), many=True
            )
            return CustomResponse().paginated_response(
                data=serializer.data, pagination=paginated_queryset.get("pagination")
            )
        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        try:
            user_id = JWTUtils.fetch_user_id(request)
            serializer = CountrySerializer(
                data=request.data, context={"user_id": user_id}
            )

            if serializer.is_valid():
                serializer.save()
                return CustomResponse(
                    general_message=serializer.data
                ).get_success_response()

            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()
        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, country_id):
        try:
            user_id = JWTUtils.fetch_user_id(request)
            country = Country.objects.get(id=country_id)
            serializer = CountrySerializer(
                country, data=request.data, context={"user_id": user_id}
            )

            if serializer.is_valid():
                serializer.save()
                return CustomResponse(
                    general_message=serializer.data
                ).get_success_response()

            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()
        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, country_id):
        try:
            country = Country.objects.get(id=country_id)
            country.delete()
            return CustomResponse(
                general_message="Country deleted successfully"
            ).get_success_response()
        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()
