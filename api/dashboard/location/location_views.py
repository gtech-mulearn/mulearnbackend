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
            countries = Country.objects.all()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            countries,
            request,
            [
                "name"
            ],
            {
                "name": "name"
            }
        )

        serializer = location_serializer.CountryRetrievalSerializer(
            paginated_queryset.get("queryset"),
            many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        serializer = location_serializer.CountryCreateEditSerializer(
            data=request.data,
            context={
                "user_id": user_id
            }
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Country created Successfully"
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, country_id):
        user_id = JWTUtils.fetch_user_id(request)
        country = Country.objects.get(id=country_id)

        serializer = location_serializer.CountryCreateEditSerializer(
            country,
            data=request.data,
            context={
                "user_id": user_id
            }
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message="Country edited successfully"
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors
        ).get_failure_response()

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
            states = State.objects.filter(
                Q(pk=state_id) |
                Q(country__pk=state_id)
            ).all()

        else:
            states = State.objects.all()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            states,
            request,
            [
                "name"
            ],
            {
                "name": "name"
            }
        )

        serializer = location_serializer.StateRetrievalSerializer(
            paginated_queryset.get("queryset"),
            many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        serializer = location_serializer.StateCreateEditSerializer(
            data=request.data,
            context={
                "user_id": user_id
            }
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message="State created successfully"
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, state_id):
        user_id = JWTUtils.fetch_user_id(request)
        state = State.objects.get(id=state_id)

        serializer = location_serializer.StateCreateEditSerializer(
            state,
            data=request.data,
            context={
                "user_id": user_id
            }
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=serializer.data
            ).get_success_response()

        return CustomResponse(
            general_message="State edited successfully"
        ).get_failure_response()

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
            zones = Zone.objects.filter(
                Q(pk=zone_id) |
                Q(state__pk=zone_id) |
                Q(state__country__pk=zone_id)
            ).all()

        else:
            zones = Zone.objects.all()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            zones,
            request,
            [
                "name"
            ],
            {
                "name": "name"
            }
        )

        serializer = location_serializer.ZoneRetrievalSerializer(
            paginated_queryset.get("queryset"),
            many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        serializer = location_serializer.ZoneCreateEditSerializer(
            data=request.data,
            context={
                "user_id": user_id
            }
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=serializer.data
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, zone_id):
        user_id = JWTUtils.fetch_user_id(request)
        zone = Zone.objects.get(id=zone_id)

        serializer = location_serializer.ZoneCreateEditSerializer(
            zone,
            data=request.data,
            context={
                "user_id": user_id
            }
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=serializer.data
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors
        ).get_failure_response()

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
            districts = District.objects.filter(
                Q(pk=district_id) |
                Q(zone__pk=district_id) |
                Q(zone__state__pk=district_id) |
                Q(zone__state__country__pk=district_id)
            ).all()

        else:
            districts = District.objects.all()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            districts,
            request,
            [
                "name"
            ],
            {
                "name": "name"
            }
        )

        serializer = location_serializer.DistrictRetrievalSerializer(
            paginated_queryset.get("queryset"),
            many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        serializer = location_serializer.DistrictCreateEditSerializer(
            data=request.data,
            context={
                "user_id": user_id
            }
        )
        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=serializer.data
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, district_id):
        user_id = JWTUtils.fetch_user_id(request)
        district = District.objects.get(id=district_id)

        serializer = location_serializer.DistrictCreateEditSerializer(
            district,
            data=request.data,
            context={
                "user_id": user_id
            }
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=serializer.data
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, district_id):
        district = District.objects.get(id=district_id)
        district.delete()

        return CustomResponse(
            general_message="District deleted successfully"
        ).get_success_response()

