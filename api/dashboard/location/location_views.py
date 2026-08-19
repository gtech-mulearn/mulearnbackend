from django.core.cache import cache
from django.db.models import Q
from rest_framework.views import APIView

from db.organization import Country, District, State, Zone
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils

from . import location_serializer
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s

# Bounded, fixed key space: these three public list endpoints take no query
# params, so each has exactly one possible cached result. Invalidated on any
# write across Country/State/Zone/District (see _invalidate_location_list_caches) —
# this data is admin-edited reference data (countries/states/zones), not a
# frequent-write path.
LOCATION_COUNTRIES_CACHE_KEY = "location_countries_list"
LOCATION_STATES_CACHE_KEY = "location_states_list"
LOCATION_ZONES_CACHE_KEY = "location_zones_list"
LOCATION_LIST_CACHE_TTL = 60 * 10  # matches api/register/register_views.py's TTL for the same class of data


def _invalidate_location_list_caches():
    """Drop all three location list caches. Called unconditionally from every
    Country/State/Zone/District write, since Country/State deletes cascade
    (on_delete=CASCADE) and can affect the states/zones lists too."""
    cache.delete(LOCATION_COUNTRIES_CACHE_KEY)
    cache.delete(LOCATION_STATES_CACHE_KEY)
    cache.delete(LOCATION_ZONES_CACHE_KEY)


def _single_record_response(queryset, serializer_cls):
    """Detail-by-id GET (queryset already filtered to a single id) kept the
    same paginated_response() envelope the list branch uses, but routing it
    through CommonUtils.get_paginated_queryset issued a redundant
    Paginator.count COUNT(*) query on top of the actual SELECT -- the count is
    already known to be 0 or 1 from the id filter. Builds the pagination dict
    directly instead, in the same shape get_paginated_queryset returns."""
    obj = queryset.first()
    objects = [obj] if obj else []
    serializer = serializer_cls(objects, many=True)
    pagination = {
        "count": len(objects),
        "totalPages": 1 if objects else 0,
        "isNext": False,
        "isPrev": False,
        "nextPage": None,
    }
    return CustomResponse().paginated_response(data=serializer.data, pagination=pagination)


class CountryDataAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Location'],
        description="Retrieve Country Data.",
        responses={200: location_serializer.LocationSerializer},
    )
    def get(self, request, country_id=None):
        if country_id:
            countries = Country.objects.filter(id=country_id).select_related(
                "created_by", "updated_by"
            )
            return _single_record_response(countries, location_serializer.LocationSerializer)

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
    @extend_schema(
        tags=['Dashboard - Location'],
        description="Create Country Data.",
        request=location_serializer.CountryCreateEditSerializer,
        responses={200: location_serializer.LocationSerializer},
    )
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
            _invalidate_location_list_caches()
            return CustomResponse(response=serializer.data).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Location'],
        description="Partially update Country Data.",
        responses={200: location_serializer.CountryCreateEditSerializer},
    )
    def patch(self, request, country_id):
        country = Country.objects.get(id=country_id)
        request_data = request.data
        request_data["updated_by"] = JWTUtils.fetch_user_id(request)
        serializer = location_serializer.CountryCreateEditSerializer(
            country, data=request_data, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            _invalidate_location_list_caches()

            return CustomResponse(response=serializer.data).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(tags=['Dashboard - Location'], description="Delete Country Data.",
        responses={200: location_serializer.LocationSerializer},
    )
    def delete(self, request, country_id):
        country = Country.objects.get(id=country_id)
        country.delete()
        _invalidate_location_list_caches()

        return CustomResponse(
            general_message="Country deleted successfully"
        ).get_success_response()


class StateDataAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Location'],
        description="Retrieve State Data.",
        responses={200: location_serializer.StateRetrievalSerializer},
    )
    def get(self, request, state_id=None):
        if state_id:
            states = State.objects.filter(pk=state_id).select_related(
                "country", "created_by", "updated_by"
            )
            return _single_record_response(states, location_serializer.StateRetrievalSerializer)

        states = State.objects.all().select_related(
            "country", "created_by", "updated_by"
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            states,
            request,
            ["name", "country__name", "created_by__full_name", "updated_by__full_name"],
            {
                "label": "name",
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
    @extend_schema(
        tags=['Dashboard - Location'],
        description="Create State Data.",
        request=location_serializer.StateCreateEditSerializer,
        responses={200: location_serializer.StateRetrievalSerializer},
    )
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
            _invalidate_location_list_caches()

            return CustomResponse(response=serializer.data).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Location'],
        description="Partially update State Data.",
        responses={200: location_serializer.StateCreateEditSerializer},
    )
    def patch(self, request, state_id):
        state = State.objects.get(id=state_id)
        request_data = request.data
        request_data["updated_by"] = JWTUtils.fetch_user_id(request)
        serializer = location_serializer.StateCreateEditSerializer(
            state, data=request_data, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            _invalidate_location_list_caches()

            return CustomResponse(response=serializer.data).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(tags=['Dashboard - Location'], description="Delete State Data.",
        responses={200: location_serializer.StateRetrievalSerializer},
    )
    def delete(self, request, state_id):
        state = State.objects.get(id=state_id)
        state.delete()
        _invalidate_location_list_caches()

        return CustomResponse(
            general_message="State deleted successfully"
        ).get_success_response()


class ZoneDataAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Location'],
        description="Retrieve Zone Data.",
        responses={200: location_serializer.ZoneRetrievalSerializer},
    )
    def get(self, request, zone_id=None):
        if zone_id:
            zones = Zone.objects.filter(pk=zone_id).select_related(
                "state", "state__country", "created_by", "updated_by"
            )
            return _single_record_response(zones, location_serializer.ZoneRetrievalSerializer)

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
                "label": "name",
                "state": "state__name",
                "country": "state__country__name",
                "created_by": "created_by__full_name",
                "created_at" : "created_at",
                "updated_by": "updated_by__full_name",
                "updated_at" : "updated_at",
            },
        )

        serializer = location_serializer.ZoneRetrievalSerializer(
            paginated_queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Location'],
        description="Create Zone Data.",
        request=location_serializer.ZoneCreateEditSerializer,
        responses={200: location_serializer.ZoneRetrievalSerializer},
    )
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
            _invalidate_location_list_caches()

            return CustomResponse(response=serializer.data).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Location'],
        description="Partially update Zone Data.",
        responses={200: location_serializer.ZoneCreateEditSerializer},
    )
    def patch(self, request, zone_id):
        zone = Zone.objects.get(id=zone_id)
        request_data = request.data
        request_data["updated_by"] = JWTUtils.fetch_user_id(request)
        serializer = location_serializer.ZoneCreateEditSerializer(
            zone, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            _invalidate_location_list_caches()

            return CustomResponse(response=serializer.data).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(tags=['Dashboard - Location'], description="Delete Zone Data.",
        responses={200: location_serializer.ZoneRetrievalSerializer},
    )
    def delete(self, request, zone_id):
        zone = Zone.objects.get(id=zone_id)
        zone.delete()
        _invalidate_location_list_caches()

        return CustomResponse(
            general_message="Zone deleted successfully"
        ).get_success_response()


class DistrictDataAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Location'],
        description="Retrieve District Data.",
        responses={200: location_serializer.DistrictRetrievalSerializer},
    )
    def get(self, request, district_id=None):
        if district_id:
            districts = District.objects.filter(pk=district_id).select_related(
                "zone", "zone__state", "zone__state__country", "created_by", "updated_by"
            )
            return _single_record_response(districts, location_serializer.DistrictRetrievalSerializer)

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
                "label": "name",
                "zone": "zone__name",
                "state": "zone__state__name",
                "country": "zone__state__country__name",
                "created_by": "created_by__full_name",
                "created_at" : "created_at",
                "updated_by": "updated_by__full_name",
                "updated_at" : "updated_at",
            },
        )

        serializer = location_serializer.DistrictRetrievalSerializer(
            paginated_queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Location'],
        description="Create District Data.",
        request=location_serializer.DistrictCreateEditSerializer,
        responses={200: location_serializer.DistrictRetrievalSerializer},
    )
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
            _invalidate_location_list_caches()

            return CustomResponse(response=serializer.data).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Location'],
        description="Partially update District Data.",
        responses={200: location_serializer.DistrictCreateEditSerializer},
    )
    def patch(self, request, district_id):
        district = District.objects.get(id=district_id)
        request_data = request.data
        request_data["updated_by"] = JWTUtils.fetch_user_id(request)
        serializer = location_serializer.DistrictCreateEditSerializer(
            district, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            _invalidate_location_list_caches()

            return CustomResponse(response=serializer.data).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(tags=['Dashboard - Location'], description="Delete District Data.",
        responses={200: location_serializer.DistrictRetrievalSerializer},
    )
    def delete(self, request, district_id):
        district = District.objects.get(id=district_id)
        district.delete()
        _invalidate_location_list_caches()

        return CustomResponse(
            general_message="District deleted successfully"
        ).get_success_response()


class CountryListApi(APIView):
    @extend_schema(tags=['Dashboard - Location'], description="Retrieve Country List Api.",
        responses={200: inline_serializer(
            name='LocationCountryListResponse',
            fields={
                'id': s.CharField(),
                'name': s.CharField(),
            },
            many=True,
        )},
    )
    def get(self, request):
        country = cache.get(LOCATION_COUNTRIES_CACHE_KEY)
        if country is None:
            country = list(Country.objects.all().values("id", "name").order_by("name"))
            cache.set(LOCATION_COUNTRIES_CACHE_KEY, country, LOCATION_LIST_CACHE_TTL)

        return CustomResponse(response=country).get_success_response()


class StateListApi(APIView):
    @extend_schema(tags=['Dashboard - Location'], description="Retrieve State List Api.",
        responses={200: inline_serializer(
            name='LocationStateListResponse',
            fields={
                'id': s.CharField(),
                'name': s.CharField(),
            },
            many=True,
        )},
    )
    def get(self, request):
        state = cache.get(LOCATION_STATES_CACHE_KEY)
        if state is None:
            state = list(State.objects.all().values("id", "name").order_by("name"))
            cache.set(LOCATION_STATES_CACHE_KEY, state, LOCATION_LIST_CACHE_TTL)

        return CustomResponse(response=state).get_success_response()


class ZoneListApi(APIView):
    @extend_schema(tags=['Dashboard - Location'], description="Retrieve Zone List Api.",
        responses={200: inline_serializer(
            name='LocationZoneListResponse',
            fields={
                'id': s.CharField(),
                'name': s.CharField(),
            },
            many=True,
        )},
    )
    def get(self, request):
        zone = cache.get(LOCATION_ZONES_CACHE_KEY)
        if zone is None:
            zone = list(Zone.objects.all().values("id", "name").order_by("name"))
            cache.set(LOCATION_ZONES_CACHE_KEY, zone, LOCATION_LIST_CACHE_TTL)

        return CustomResponse(response=zone).get_success_response()
