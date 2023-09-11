from django.db.models import Q
from rest_framework.views import APIView

from db.organization import Country, District, State, Zone
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from .location_serializer import (
    CountrySerializer,
    StateSerializer,
    ZoneSerializer,
    DistrictSerializer,
CountryRetrivalSerializer
)


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

            serializer = CountryRetrivalSerializer(
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


class StateDataAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, state_id=None):
        try:
            if state_id:
                states = State.objects.filter(
                    Q(pk=state_id) | Q(country__pk=state_id)
                ).all()
            else:
                states = State.objects.all()

            paginated_queryset = CommonUtils.get_paginated_queryset(
                states, request, ["name"], {"name": "name"}
            )

            serializer = StateSerializer(paginated_queryset.get("queryset"), many=True)

            return CustomResponse().paginated_response(
                data=serializer.data, pagination=paginated_queryset.get("pagination")
            )
        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        try:
            user_id = JWTUtils.fetch_user_id(request)
            serializer = StateSerializer(
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
    def patch(self, request, state_id):
        try:
            user_id = JWTUtils.fetch_user_id(request)
            state = State.objects.get(id=state_id)
            serializer = StateSerializer(
                state, data=request.data, context={"user_id": user_id}
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
    def delete(self, request, state_id):
        try:
            state = State.objects.get(id=state_id)
            state.delete()
            return CustomResponse(
                general_message="State deleted successfully"
            ).get_success_response()
        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()


class ZoneDataAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, zone_id=None):
        try:
            if zone_id:
                zones = Zone.objects.filter(
                    Q(pk=zone_id) | Q(state__pk=zone_id) | Q(state__country__pk=zone_id)
                ).all()
            else:
                zones = Zone.objects.all()

            paginated_queryset = CommonUtils.get_paginated_queryset(
                zones, request, ["name"], {"name": "name"}
            )

            serializer = ZoneSerializer(paginated_queryset.get("queryset"), many=True)
            return CustomResponse().paginated_response(
                data=serializer.data, pagination=paginated_queryset.get("pagination")
            )
        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        try:
            user_id = JWTUtils.fetch_user_id(request)
            serializer = ZoneSerializer(data=request.data, context={"user_id": user_id})
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
    def patch(self, request, zone_id):
        try:
            user_id = JWTUtils.fetch_user_id(request)
            zone = Zone.objects.get(id=zone_id)
            serializer = ZoneSerializer(
                zone, data=request.data, context={"user_id": user_id}
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
    def delete(self, request, zone_id):
        try:
            zone = Zone.objects.get(id=zone_id)
            zone.delete()
            return CustomResponse(
                general_message="Zone deleted successfully"
            ).get_success_response()
        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()


class DistrictDataAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, district_id=None):
        try:
            if district_id:
                districts = District.objects.filter(
                    Q(pk=district_id)
                    | Q(zone__pk=district_id)
                    | Q(zone__state__pk=district_id)
                    | Q(zone__state__country__pk=district_id)
                ).all()
            else:
                districts = District.objects.all()

            paginated_queryset = CommonUtils.get_paginated_queryset(
                districts, request, ["name"], {"name": "name"}
            )

            serializer = DistrictSerializer(
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
            serializer = DistrictSerializer(
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
    def patch(self, request, district_id):
        try:
            user_id = JWTUtils.fetch_user_id(request)
            district = District.objects.get(id=district_id)
            serializer = DistrictSerializer(
                district, data=request.data, context={"user_id": user_id}
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
    def delete(self, request, district_id):
        try:
            district = District.objects.get(id=district_id)
            district.delete()
            return CustomResponse(
                general_message="District deleted successfully"
            ).get_success_response()
        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()
