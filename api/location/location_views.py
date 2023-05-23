import uuid
from datetime import datetime

from rest_framework.views import APIView

from db.organization import Country, State, District, Zone
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from .serializer import CountrySerializer, StateSerializer, DistrictSerializer, ZoneSerializer, UserCountrySerializer, \
    UserStateSerializer


class CountryData(APIView):
    permission_classes = [CustomizePermission]

    # Params available:[sortBy, search, perPage, pageIndex]
    def get(self, request):
        countries = Country.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(countries, request, ['id', 'name'])

        serializer = CountrySerializer(paginated_queryset.get('queryset'), many=True)
        return CustomResponse(response={"countries": serializer.data,
                                        "pagination": paginated_queryset.get("pagination")}).get_success_response()

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
            'name': request.data.get('new_name'),
            'updated_by': user_id,
            'updated_at': updated_at,
        }

        country = Country.objects.get(name=request.data.get('old_name'))
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


class StateData(APIView):
    permission_classes = [CustomizePermission]

    # Params available:[sortBy, search, perPage, pageIndex]
    def get(self, request, country):
        country_obj = Country.objects.filter(name=country).first()
        if not country_obj:
            return CustomResponse(general_message=["Country not found"]).get_failure_response()
        country_id = country_obj.id
        states = State.objects.filter(country=country_id)
        paginated_queryset = CommonUtils.get_paginated_queryset(states, request, ['id', 'name'])

        serializer = StateSerializer(paginated_queryset, many=True)
        return CustomResponse(response={'states': serializer.data,
                                        'pagination': paginated_queryset.get("pagination")}).get_success_response()

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

        state = State.objects.filter(name=request.data.get('old_name'), country=country_id).first()

        if request.data.get('country'):
            country_obj = Country.objects.filter(name=request.data.get("country")).first()
            if not country_obj:
                return CustomResponse(general_message=["Country not found"]).get_failure_response()
            if request.data.get('new_name'):
                state_exist = State.objects.filter(name=request.data.get('new_name'), country=country_obj.id).first()
                if state_exist:
                    return CustomResponse(general_message=
                        [f"State already exists for {request.data.get('country')}"]).get_failure_response()
                request.data['name'] = request.data.get('new_name')
            else:
                state_exist = State.objects.filter(name=request.data.get('old_name'), country=country_obj.id).first()
                if state_exist:
                    return CustomResponse(general_message=
                        [f"State already exists for {request.data.get('country')}"]).get_failure_response()
            country_id = country_obj.id
            request.data['country'] = country_id

        if request.data.get('new_name') and not request.data.get('country'):
            state_exist = State.objects.filter(name=request.data.get('new_name'), country=country_id).first()
            if state_exist:
                return CustomResponse(general_message=[f"State already exists for {country}"]).get_failure_response()
            request.data['name'] = request.data.get('new_name')

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


class ZoneData(APIView):
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

        serializer = ZoneSerializer(paginated_queryset, many=True)
        return CustomResponse(response={"zones": serializer.data,
                                        "pagination": paginated_queryset.get("pagination")}).get_success_response()

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

        zone = Zone.objects.filter(name=request.data.get('old_name'), state=state_id).first()
        if not zone:
            return CustomResponse(general_message=["Zone not found"]).get_failure_response()

        if request.data.get('state'):
            state_obj = State.objects.filter(name=request.data.get("state"), country=country_id).first()
            if not state_obj:
                return CustomResponse(general_message=["State not found"]).get_failure_response()
            if request.data.get('new_name'):
                zone_exists = Zone.objects.filter(name=request.data.get('new_name'), state=state_obj.id).first()
                if zone_exists:
                    return CustomResponse(general_message=
                    [f"Zone already exist for {request.data.get('state')}"]).get_failure_response()
                request.data['name'] = request.data.get('new_name')
            else:
                zone_exists = Zone.objects.filter(name=request.data.get('old_name'), state=state_obj.id).first()
                if zone_exists:
                    return CustomResponse(general_message=
                            [f"Zone already exist for {request.data.get('state')}"]).get_failure_response()
            request.data['state'] = state_obj.id

        if request.data.get('new_name') and not request.data.get('state'):
            zone_exists = Zone.objects.filter(name=request.data.get('new_name'), state=state_id).first()
            if zone_exists:
                return CustomResponse(general_message=[f"Zone already exists for {state}"]).get_failure_response()
            request.data['name'] = request.data.get('new_name')

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


class DistrictData(APIView):
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
        serializer = DistrictSerializer(paginated_queryset, many=True)
        return CustomResponse(response={"districts": serializer.data,"pagination": paginated_queryset.get("pagination")}).get_success_response()

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

        district = District.objects.filter(name=request.data.get('old_name'), zone=zone_id).first()
        if not district:
            return CustomResponse(general_message=["District not found"]).get_failure_response()

        if request.data.get('zone'):
            zone_obj = Zone.objects.filter(name=request.data.get("zone"), state=state_id).first()
            if not zone_obj:
                return CustomResponse(general_message=["Zone not found"]).get_failure_response()
            if request.data.get('new_name'):
                district_exist = District.objects.filter(name=request.data.get('new_name'), zone=zone_obj.id).first()
                if district_exist:
                    return CustomResponse(general_message=
                            [f"District already exists for {request.data.get('zone')}"]).get_failure_response()
                request.data['name'] = request.data.get('new_name')
            else:
                district_exist = District.objects.filter(name=request.data.get('old_name'), zone=zone_obj.id).first()
                if district_exist:
                    return CustomResponse(general_message=
                    [f"District already exists for {request.data.get('zone')}"]).get_failure_response()

            request.data['zone'] = zone_obj.id

        if request.data.get('new_name') and not request.data.get('zone'):
            district_exist = District.objects.filter(name=request.data.get('new_name'), zone=zone_id).first()
            if district_exist:
                return CustomResponse(general_message=[f"District already exists for {zone}"]).get_failure_response()
            request.data['name'] = request.data.get('new_name')

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


class UserCountryAPI(APIView):

    def get(self, request):

        country = Country.objects.all()
        if country is None:
            return CustomResponse(general_message="No data available").get_success_response()
        country_serializer = UserCountrySerializer(country, many=True).data
        return CustomResponse(response=country_serializer).get_success_response()


class UserStateAPI(APIView):

    def get(self, request):

        country_name = request.data.get('country')

        country_object = Country.objects.filter(name=country_name).first()
        if country_object is None:
            return CustomResponse(general_message='No country data available').get_success_response()

        state_object = State.objects.filter(country_id=country_object).all()
        if len(state_object) == 0:
            return CustomResponse(general_message='No state data available for given country').get_success_response()

        state_serializer = UserStateSerializer(state_object, many=True).data
        return CustomResponse(response=state_serializer).get_success_response()


class UserZoneAPI(APIView):

    def get(self, request):

        state_name = request.data.get('state')

        state_object = State.objects.filter(name=state_name).first()
        if state_object is None:
            return CustomResponse(general_message='No state data available').get_success_response()

        zone_object = Zone.objects.filter(state_id=state_object).all()
        if len(zone_object) == 0:
            return CustomResponse(general_message='No zone data available for given country').get_success_response()

        zone_serializer = UserStateSerializer(zone_object, many=True).data
        return CustomResponse(response=zone_serializer).get_success_response()

