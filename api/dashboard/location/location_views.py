import uuid
from datetime import datetime

from rest_framework.views import APIView

from db.organization import Country, State, District, Zone
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from .serializer import CountrySerializer, StateSerializer, DistrictSerializer, ZoneSerializer


class CountryDataAPI(APIView):
    permission_classes = [CustomizePermission]

    # Params available:[sortBy, search, perPage, pageIndex]
    def get(self, request):
        countries = Country.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(countries, request, ['id', 'name'])

        serializer = CountrySerializer(paginated_queryset.get('queryset'), many=True)
        print(serializer.data)
        return CustomResponse().paginated_response(data=serializer.data, pagination=paginated_queryset.get('pagination'))

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(general_message=["User not found"]).get_failure_response()

        country = Country.objects.filter(name=request.data.get('name')).first()
        if country:
            return CustomResponse(general_message=["Country already exists"]).get_failure_response()

        created_at = datetime.now()
        updated_at = datetime.now()

        data = {
            'id': str(uuid.uuid4()),
            'name': request.data.get('name'),
            'updated_by': user_id,
            'created_by': user_id,
            'updated_at': updated_at,
            'created_at': created_at,
        }

        serializer = CountrySerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(general_message=[serializer.errors]).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def put(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(general_message=["User not found"]).get_failure_response()

        updated_at = datetime.now()

        data = {
            'name': request.data.get('newName'),
            'updated_by': user_id,
            'updated_at': updated_at,
        }

        country = Country.objects.get(name=request.data.get('oldName'))
        serializer = CountrySerializer(country, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(general_message=[serializer.errors]).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def delete(self, request):
        country = Country.objects.filter(name=request.data.get('name')).first()
        if not country:
            return CustomResponse(general_message=["Country not found"]).get_failure_response()

        country.delete()
        return CustomResponse(response={"response": "Country deleted successfully"}).get_success_response()


class StateDataAPI(APIView):
    permission_classes = [CustomizePermission]

    # Params available:[sortBy, search, perPage, pageIndex]
    def get(self, request, country):
        country_obj = Country.objects.filter(name=country).first()
        if not country_obj:
            return CustomResponse(general_message=["Country not found"]).get_failure_response()
        country_id = country_obj.id
        states = State.objects.filter(country=country_id)
        paginated_queryset = CommonUtils.get_paginated_queryset(states, request, ['id', 'name'])

        serializer = StateSerializer(paginated_queryset.get('queryset'), many=True)
        return CustomResponse().paginated_response(data=serializer.data, pagination=paginated_queryset.get('pagination'))

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def post(self, request, country):
        user_id = JWTUtils.fetch_user_id(request)
        country_obj = Country.objects.filter(name=country).first()

        if not user_id:
            return CustomResponse(general_message=["User not found"]).get_failure_response()

        if not country_obj:
            return CustomResponse(general_message=["Country not found"]).get_failure_response()

        country_id = country_obj.id

        state = State.objects.filter(name=request.data.get('name'), country=country_id).first()
        if state:
            return CustomResponse(general_message=["State already exists"]).get_failure_response()

        created_at = datetime.now()
        updated_at = datetime.now()

        data = {
            'id': str(uuid.uuid4()),
            'name': request.data.get('name'),
            'country': country_id,
            'updated_by': user_id,
            'created_by': user_id,
            'updated_at': updated_at,
            'created_at': created_at,
        }

        serializer = StateSerializer(data=data)

        if serializer.is_valid():
            print(serializer.validated_data)
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(general_message=[serializer.errors]).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def put(self, request, country):
        user_id = JWTUtils.fetch_user_id(request)

        country_obj = Country.objects.filter(name=country).first()
        if not country_obj:
            return CustomResponse(general_message=["Country not found"]).get_failure_response()
        country_id = country_obj.id

        if not user_id:
            return CustomResponse(general_message=["User not found"]).get_failure_response()

        state = State.objects.filter(name=request.data.get('oldName'), country=country_id).first()

        if request.data.get('country'):
            country_obj = Country.objects.filter(name=request.data.get("country")).first()
            if not country_obj:
                return CustomResponse(general_message=["Country not found"]).get_failure_response()
            if request.data.get('newName'):
                state_exist = State.objects.filter(name=request.data.get('newName'), country=country_obj.id).first()
                if state_exist:
                    return CustomResponse(general_message=
                        [f"State already exists for {request.data.get('country')}"]).get_failure_response()
                request.data['name'] = request.data.get('newName')
            else:
                state_exist = State.objects.filter(name=request.data.get('oldName'), country=country_obj.id).first()
                if state_exist:
                    return CustomResponse(general_message=
                        [f"State already exists for {request.data.get('country')}"]).get_failure_response()
            country_id = country_obj.id
            request.data['country'] = country_id

        if request.data.get('newName') and not request.data.get('country'):
            state_exist = State.objects.filter(name=request.data.get('newName'), country=country_id).first()
            if state_exist:
                return CustomResponse(general_message=[f"State already exists for {country}"]).get_failure_response()
            request.data['name'] = request.data.get('newName')

        request.data['updated_by'] = user_id
        request.data['updated_at'] = datetime.now()

        serializer = StateSerializer(state, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(general_message=[serializer.errors]).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def delete(self, request, country):
        country_obj = Country.objects.filter(name=country).first()
        if not country_obj:
            return CustomResponse(general_message=["Country not found"]).get_failure_response()
        country_id = country_obj.id
        state = State.objects.filter(name=request.data.get('name'), country=country_id).first()
        if not state:
            return CustomResponse(general_message=["State not found"]).get_failure_response()

        state.delete()
        return CustomResponse(response={"response": "State deleted successfully"}).get_success_response()


class ZoneDataAPI(APIView):
    permission_classes = [CustomizePermission]

    # Params available:[sortBy, search, perPage, pageIndex]
    def get(self, request, country, state):
        country_obj = Country.objects.filter(name=country).first()
        if not country_obj:
            return CustomResponse(general_message=["Country not found"]).get_failure_response()
        country_id = country_obj.id
        state_obj = State.objects.filter(name=state, country=country_id).first()
        if not state_obj:
            return CustomResponse(general_message=["State not found"]).get_failure_response()

        state_id = state_obj.id
        zones = Zone.objects.filter(state=state_id)
        paginated_queryset = CommonUtils.get_paginated_queryset(zones, request, ['id', 'name'])

        serializer = ZoneSerializer(paginated_queryset.get('queryset'), many=True)
        return CustomResponse().paginated_response(data=serializer.data, pagination=paginated_queryset.get('pagination'))

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def post(self, request, state, country):
        user_id = JWTUtils.fetch_user_id(request)
        country_obj = Country.objects.filter(name=country).first()
        if not country_obj:
            return CustomResponse(general_message=["Country not found"]).get_failure_response()
        country_id = country_obj.id
        state_obj = State.objects.filter(name=state, country=country_id).first()
        if not state_obj:
            return CustomResponse(general_message=["State not found"]).get_failure_response()

        state_id = state_obj.id
        if not user_id:
            return CustomResponse(general_message=["User not found"]).get_failure_response()

        zone = Zone.objects.filter(name=request.data.get('name'), state=state_id).first()
        if zone:
            return CustomResponse(general_message=["Zone already exists"]).get_failure_response()

        created_at = datetime.now()
        updated_at = datetime.now()

        data = {
            'id': str(uuid.uuid4()),
            'name': request.data.get('name'),
            'state': state_id,
            'updated_by': user_id,
            'created_by': user_id,
            'updated_at': updated_at,
            'created_at': created_at,
        }

        serializer = ZoneSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(general_message=[serializer.errors]).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def put(self, request, state, country):
        user_id = JWTUtils.fetch_user_id(request)
        country_obj = Country.objects.filter(name=country).first()
        if not country_obj:
            return CustomResponse(general_message=["Country not found"]).get_failure_response()
        country_id = country_obj.id
        state_obj = State.objects.filter(name=state, country=country_id).first()
        if not state_obj:
            return CustomResponse(general_message=["State not found"]).get_failure_response()

        state_id = state_obj.id

        if not user_id:
            return CustomResponse(general_message=["User not found"]).get_failure_response()

        zone = Zone.objects.filter(name=request.data.get('oldName'), state=state_id).first()
        if not zone:
            return CustomResponse(general_message=["Zone not found"]).get_failure_response()

        if request.data.get('state'):
            state_obj = State.objects.filter(name=request.data.get("state"), country=country_id).first()
            if not state_obj:
                return CustomResponse(general_message=["State not found"]).get_failure_response()
            if request.data.get('newName'):
                zone_exists = Zone.objects.filter(name=request.data.get('newName'), state=state_obj.id).first()
                if zone_exists:
                    return CustomResponse(general_message=
                    [f"Zone already exist for {request.data.get('state')}"]).get_failure_response()
                request.data['name'] = request.data.get('newName')
            else:
                zone_exists = Zone.objects.filter(name=request.data.get('oldName'), state=state_obj.id).first()
                if zone_exists:
                    return CustomResponse(general_message=
                            [f"Zone already exist for {request.data.get('state')}"]).get_failure_response()
            request.data['state'] = state_obj.id

        if request.data.get('newName') and not request.data.get('state'):
            zone_exists = Zone.objects.filter(name=request.data.get('newName'), state=state_id).first()
            if zone_exists:
                return CustomResponse(general_message=[f"Zone already exists for {state}"]).get_failure_response()
            request.data['name'] = request.data.get('newName')

        request.data['updated_by'] = user_id
        request.data['updated_at'] = datetime.now()

        serializer = ZoneSerializer(zone, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(general_message=[serializer.errors]).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def delete(self, request, state, country):
        country_obj = Country.objects.filter(name=country).first()
        if not country_obj:
            return CustomResponse(general_message=["Country not found"]).get_failure_response()
        country_id = country_obj.id
        state_obj = State.objects.filter(name=state, country=country_id).first()
        if not state_obj:
            return CustomResponse(general_message=["State not found"]).get_failure_response()
        state_id = state_obj.id
        zone = Zone.objects.filter(name=request.data.get('name'), state=state_id).first()
        if not zone:
            return CustomResponse(general_message=["Zone not found"]).get_failure_response()

        zone.delete()
        return CustomResponse(response={"response": "Zone deleted successfully"}).get_success_response()


class DistrictDataAPI(APIView):
    permission_classes = [CustomizePermission]

    # Params available:[sortBy, search, perPage, pageIndex]
    def get(self, request, country, state, zone):
        country_obj = Country.objects.filter(name=country).first()
        if not country_obj:
            return CustomResponse(general_message=["Country not found"]).get_failure_response()
        country_id = country_obj.id
        state_obj = State.objects.filter(name=state, country=country_id).first()
        if not state_obj:
            return CustomResponse(general_message=["State not found"]).get_failure_response()
        state_id = state_obj.id
        zone_obj = Zone.objects.filter(name=zone, state=state_id).first()
        if not zone_obj:
            return CustomResponse(general_message=["Zone not found"]).get_failure_response()
        zone_id = zone_obj.id

        districts = District.objects.filter(zone=zone_id)
        paginated_queryset = CommonUtils.get_paginated_queryset(districts, request,['id', 'name'])
        serializer = DistrictSerializer(paginated_queryset.get('queryset'), many=True)
        return CustomResponse().paginated_response(data=serializer.data, pagination=paginated_queryset.get('pagination'))
    @RoleRequired(roles=[RoleType.ADMIN, ])
    def post(self, request, country, state, zone):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(general_message=["User not found"]).get_failure_response()

        country_obj = Country.objects.filter(name=country).first()
        if not country_obj:
            return CustomResponse(general_message=["Country not found"]).get_failure_response()
        country_id = country_obj.id
        state_obj = State.objects.filter(name=state, country=country_id).first()
        if not state_obj:
            return CustomResponse(general_message=["State not found"]).get_failure_response()
        state_id = state_obj.id
        zone_obj = Zone.objects.filter(name=zone, state=state_id).first()
        if not zone_obj:
            return CustomResponse(general_message=["Zone not found"]).get_failure_response()
        zone_id = zone_obj.id
        if not zone_id:
            return CustomResponse(general_message=["Zone not found"]).get_failure_response()

        district = District.objects.filter(name=request.data.get('name'), zone=zone_id).first()
        if district:
            return CustomResponse(general_message=["District already exists"]).get_failure_response()

        created_at = datetime.now()
        updated_at = datetime.now()

        data = {
            'id': str(uuid.uuid4()),
            'name': request.data.get('name'),
            'zone': zone_id,
            'updated_by': user_id,
            'created_by': user_id,
            'updated_at': updated_at,
            'created_at': created_at,
        }

        serializer = DistrictSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(general_message=[serializer.errors]).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def put(self, request, country, state, zone):
        user_id = JWTUtils.fetch_user_id(request)

        if not user_id:
            return CustomResponse(general_message=["User not found"]).get_failure_response()

        country_obj = Country.objects.filter(name=country).first()
        if not country_obj:
            return CustomResponse(general_message=["Country not found"]).get_failure_response()
        country_id = country_obj.id
        state_obj = State.objects.filter(name=state, country=country_id).first()
        if not state_obj:
            return CustomResponse(general_message=["State not found"]).get_failure_response()
        state_id = state_obj.id
        zone_obj = Zone.objects.filter(name=zone, state=state_id).first()
        if not zone_obj:
            return CustomResponse(general_message=["Zone not found"]).get_failure_response()
        zone_id = zone_obj.id

        district = District.objects.filter(name=request.data.get('oldName'), zone=zone_id).first()
        if not district:
            return CustomResponse(general_message=["District not found"]).get_failure_response()

        if request.data.get('zone'):
            zone_obj = Zone.objects.filter(name=request.data.get("zone"), state=state_id).first()
            if not zone_obj:
                return CustomResponse(general_message=["Zone not found"]).get_failure_response()
            if request.data.get('newName'):
                district_exist = District.objects.filter(name=request.data.get('newName'), zone=zone_obj.id).first()
                if district_exist:
                    return CustomResponse(general_message=
                            [f"District already exists for {request.data.get('zone')}"]).get_failure_response()
                request.data['name'] = request.data.get('newName')
            else:
                district_exist = District.objects.filter(name=request.data.get('oldName'), zone=zone_obj.id).first()
                if district_exist:
                    return CustomResponse(general_message=
                    [f"District already exists for {request.data.get('zone')}"]).get_failure_response()

            request.data['zone'] = zone_obj.id

        if request.data.get('newName') and not request.data.get('zone'):
            district_exist = District.objects.filter(name=request.data.get('newName'), zone=zone_id).first()
            if district_exist:
                return CustomResponse(general_message=[f"District already exists for {zone}"]).get_failure_response()
            request.data['name'] = request.data.get('newName')

        request.data['updated_by'] = user_id
        request.data['updated_at'] = datetime.now()

        serializer = DistrictSerializer(district, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(general_message=[serializer.errors]).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def delete(self, request, country, state, zone):
        country_obj = Country.objects.filter(name=country).first()
        if not country_obj:
            return CustomResponse(general_message=["Country not found"]).get_failure_response()
        country_id = country_obj.id
        state_obj = State.objects.filter(name=state, country=country_id).first()
        if not state_obj:
            return CustomResponse(general_message=["State not found"]).get_failure_response()
        state_id = state_obj.id
        zone_obj = Zone.objects.filter(name=zone, state=state_id).first()
        if not zone_obj:
            return CustomResponse(general_message=["Zone not found"]).get_failure_response()
        zone_id = zone_obj.id
        district = District.objects.filter(name=request.data.get('name'), zone=zone_id).first()
        if not district:
            return CustomResponse(general_message=["District not found"]).get_failure_response()

        district.delete()
        return CustomResponse(response={"response": "District deleted successfully"}).get_success_response()



