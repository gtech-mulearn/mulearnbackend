from django.db.models import Q
from rest_framework.views import APIView

from db.organization import Country, District, State, Zone
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils

from . import location_serializer


class CountryDataAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, country_id=None):
        if country_id:
            countries = Country.objects.filter(id=country_id)
        else:
            countries = Country.objects.select_related("created_by", "updated_by")

        paginated_queryset = CommonUtils.get_paginated_queryset(
            countries,
            request,
            [
                "name",
                "created_by__full_name",
                "updated_by__full_name",
            ],
            {
                "label": "name",
                "created_by": "created_by__full_name",
                "created_at": "created_at",
                "updated_by": "updated_by__full_name",
                "updated_at": "updated_at",
            },
        )

        serializer = location_serializer.LocationSerializer(
            paginated_queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        request_data = request.data
        request_data["created_by"] = request_data[
            "updated_by"
        ] = JWTUtils.fetch_user_id(request)
        serializer = location_serializer.CountryCreateEditSerializer(
            data=request_data,
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, country_id):
        country = Country.objects.get(id=country_id)
        request_data = request.data
        request_data["updated_by"] = JWTUtils.fetch_user_id(request)
        serializer = location_serializer.CountryCreateEditSerializer(
            country, data=request_data, partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(response=serializer.data).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, country_id):
        country = Country.objects.get(id=country_id)
        country.delete()

        return CustomResponse(
            general_message="Country deleted successfully"
        ).get_success_response()


class StateDataAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, state_id=None):
        if state_id:
            states = State.objects.filter(pk=state_id).select_related(
                "country", "created_by", "updated_by"
            )
        else:
            states = State.objects.all().select_related(
                "country", "created_by", "updated_by"
            )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            states,
            request,
            ["name", "country__name", "created_by__full_name", "updated_by__full_name"],
            {
                "name": "name",
                "country": "country__name",
                "created_by": "created_by__full_name",
                "created_at": "created_at",
                "updated_by": "updated_by__full_name",
                "updated_at": "updated_at",
            },
        )

        serializer = location_serializer.StateRetrievalSerializer(
            paginated_queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        request_data = request.data
        request_data["created_by"] = request_data[
            "updated_by"
        ] = JWTUtils.fetch_user_id(request)

        serializer = location_serializer.StateCreateEditSerializer(
            data=request_data,
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(response=serializer.data).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, state_id):
        state = State.objects.get(id=state_id)
        request_data = request.data
        request_data["updated_by"] = JWTUtils.fetch_user_id(request)
        serializer = location_serializer.StateCreateEditSerializer(
            state, data=request_data, partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(response=serializer.data).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, state_id):
        state = State.objects.get(id=state_id)
        state.delete()

        return CustomResponse(
            general_message="State deleted successfully"
        ).get_success_response()


class ZoneDataAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, zone_id=None):
        if zone_id:
            zones = Zone.objects.filter(pk=zone_id)
        else:
            zones = Zone.objects.all().select_related(
                "state", "state__country", "created_by", "updated_by"
            )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            zones,
            request,
            [
                "name",
                "state__name",
                "state__country__name",
                "created_by__full_name",
                "updated_by__full_name",
            ],
            {
                "name": "name",
                "state": "state__name",
                "country": "state__country__name",
                "created_by": "created_by__full_name",
                "updated_by": "updated_by__full_name",
            },
        )

        serializer = location_serializer.ZoneRetrievalSerializer(
            paginated_queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        request_data = request.data
        request_data["created_by"] = request_data[
            "updated_by"
        ] = JWTUtils.fetch_user_id(request)
        serializer = location_serializer.ZoneCreateEditSerializer(
            data=request.data,
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(response=serializer.data).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, zone_id):
        zone = Zone.objects.get(id=zone_id)
        request_data = request.data
        request_data["updated_by"] = JWTUtils.fetch_user_id(request)
        serializer = location_serializer.ZoneCreateEditSerializer(
            zone, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(response=serializer.data).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, zone_id):
        zone = Zone.objects.get(id=zone_id)
        zone.delete()

        return CustomResponse(
            general_message="Zone deleted successfully"
        ).get_success_response()


class DistrictDataAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, district_id=None):
        if district_id:
            districts = District.objects.filter(pk=district_id)

        else:
            districts = District.objects.all().select_related(
                "zone",
                "zone__state",
                "zone__state__country",
                "created_by",
                "updated_by",
            )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            districts,
            request,
            [
                "name",
                "zone__name",
                "zone__state__name",
                "created_by__full_name",
                "updated_by__full_name",
            ],
            {
                "name": "name",
                "zone": "zone__name",
                "state": "zone__state__name",
                "country": "zone__state__country__name",
                "created_by": "created_by__full_name",
                "updated_by": "updated_by__full_name",
            },
        )

        serializer = location_serializer.DistrictRetrievalSerializer(
            paginated_queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        request_data = request.data
        request_data["created_by"] = request_data[
            "updated_by"
        ] = JWTUtils.fetch_user_id(request)

        serializer = location_serializer.DistrictCreateEditSerializer(
            data=request.data,
        )
        if serializer.is_valid():
            serializer.save()

            return CustomResponse(response=serializer.data).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, district_id):
        district = District.objects.get(id=district_id)
        request_data = request.data
        request_data["updated_by"] = JWTUtils.fetch_user_id(request)
        serializer = location_serializer.DistrictCreateEditSerializer(
            district, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(response=serializer.data).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, district_id):
        district = District.objects.get(id=district_id)
        district.delete()

        return CustomResponse(
            general_message="District deleted successfully"
        ).get_success_response()


class CountryListApi(APIView):
    def get(self, request):
        country = Country.objects.all().values("id", "name").order_by("name")

        return CustomResponse(response=country).get_success_response()


class StateListApi(APIView):
    def get(self, request):
        state = State.objects.all().values("id", "name").order_by("name")

        return CustomResponse(response=state).get_success_response()


class ZoneListApi(APIView):
    def get(self, request):
        zone = Zone.objects.all().values("id", "name").order_by("name")

        return CustomResponse(response=zone).get_success_response()
