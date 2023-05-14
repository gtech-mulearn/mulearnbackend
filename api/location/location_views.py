import uuid

from rest_framework.views import APIView
from db.organization import Country, State, District, Zone
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from .serializer import CountrySerializer, StateSerializer, DistrictSerializer, ZoneSerializer
from db.user import User
from datetime import datetime
from utils.permission import CustomizePermission, JWTUtils, RoleRequired


class CountryData(APIView):
    permission_classes = [CustomizePermission]

    # Params available:[sortBy, search, perPage]
    def get(self, request):
        countries = Country.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(countries, request,
                                                                ['id', 'name'])
        serializer = CountrySerializer(paginated_queryset, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(response={"response": "User not found"}).get_failure_response()

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
        return CustomResponse(response=serializer.errors).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def put(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(response={"response": "User not found"}).get_failure_response()

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
        return CustomResponse(response=serializer.errors).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def delete(self, request):
        country = Country.objects.filter(name=request.data.get('name')).first()
        if not country:
            return CustomResponse(response={"response": "Country not found"}).get_failure_response()

        country.delete()
        return CustomResponse(response={"response": "Country deleted successfully"}).get_success_response()


class StateData(APIView):
    permission_classes = [CustomizePermission]

    # Params available:[sortBy, search, perPage]
    def get(self, request, country):
        country_id = Country.objects.filter(name=country).first().id
        states = State.objects.filter(country=country_id)
        paginated_queryset = CommonUtils.get_paginated_queryset(states, request,
                                                                ['id', 'name'])
        serializer = StateSerializer(paginated_queryset, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def post(self, request, country):
        user_id = JWTUtils.fetch_user_id(request)
        country_id = Country.objects.filter(name=country).first().id

        print(country_id)

        if not user_id:
            return CustomResponse(response={"response": "User not found"}).get_failure_response()

        if not country_id:
            return CustomResponse(response={"response": "Country not found"}).get_failure_response()

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
        return CustomResponse(response=serializer.errors).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def put(self, request, country):
        user_id = JWTUtils.fetch_user_id(request)

        if not user_id:
            return CustomResponse(response={"response": "User not found"}).get_failure_response()

        if request.data.get('country'):
            country_id = Country.objects.filter(name=country).first().id
            if not country_id:
                return CustomResponse(response={"response": "Country not found"}).get_failure_response()
            request.data['country'] = country_id

        if request.data.get('new_name'):
            request.data['name'] = request.data.get('new_name')

        request.data['updated_by'] = user_id
        request.data['updated_at'] = datetime.now()

        state = State.objects.filter(name=request.data.get('old_name')).first()
        serializer = StateSerializer(state, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(response=serializer.errors).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def delete(self, request, country):
        state = State.objects.filter(name=request.data.get('name')).first()
        if not state:
            return CustomResponse(response={"response": "State not found"}).get_failure_response()

        state.delete()
        return CustomResponse(response={"response": "State deleted successfully"}).get_success_response()


class ZoneData(APIView):
    permission_classes = [CustomizePermission]

    # Params available:[sortBy, search, perPage]
    def get(self, request, state):
        state_id = State.objects.filter(name=state).first().id
        zones = Zone.objects.filter(state=state_id)
        paginated_queryset = CommonUtils.get_paginated_queryset(zones, request,
                                                                ['id', 'name'])
        serializer = ZoneSerializer(paginated_queryset, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def post(self, request, state):
        mu_id = request.data.get('mu_id')
        user_id = User.objects.filter(mu_id=mu_id).first().id
        state_id = State.objects.filter(name=state).first().id
        if not user_id:
            return CustomResponse(response={"response": "User not found"}).get_failure_response()

        if not state_id:
            return CustomResponse(response={"response": "State not found"}).get_failure_response()

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
        return CustomResponse(response=serializer.errors).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def put(self, request, state):
        mu_id = request.data.get('mu_id')
        user_id = User.objects.filter(mu_id=mu_id).first().id

        if not user_id:
            return CustomResponse(response={"response": "User not found"}).get_failure_response()

        zone = Zone.objects.filter(name=request.data.get('old_name')).first()
        if not zone:
            return CustomResponse(response={"response": "Zone not found"}).get_failure_response()

        request.data['name'] = request.data.get('new_name')
        request.data['updated_by'] = user_id
        request.data['updated_at'] = datetime.now()

        serializer = ZoneSerializer(zone, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(response=serializer.errors).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def delete(self, request, state):
        zone = Zone.objects.filter(name=request.data.get('name')).first()
        if not zone:
            return CustomResponse(response={"response": "Zone not found"}).get_failure_response()

        zone.delete()
        return CustomResponse(response={"response": "Zone deleted successfully"}).get_success_response()


class DistrictData(APIView):
    permission_classes = [CustomizePermission]

    # Params available:[sortBy, search, perPage]
    def get(self, request, zone):
        zone_id = Zone.objects.filter(name=zone).first().id
        districts = District.objects.filter(zone=zone_id)
        paginated_queryset = CommonUtils.get_paginated_queryset(districts, request,
                                                                ['id', 'name'])
        serializer = DistrictSerializer(paginated_queryset, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def post(self, request, zone):
        mu_id = request.data.get('mu_id')
        user_id = User.objects.filter(mu_id=mu_id).first().id
        zone_id = Zone.objects.filter(name=zone).first().id
        if not user_id:
            return CustomResponse(response={"response": "User not found"}).get_failure_response()

        if not zone_id:
            return CustomResponse(response={"response": "Zone not found"}).get_failure_response()

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
        return CustomResponse(response=serializer.errors).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def put(self, request, zone):
        mu_id = request.data.get('mu_id')
        user_id = User.objects.filter(mu_id=mu_id).first().id

        if not user_id:
            return CustomResponse(response={"response": "User not found"}).get_failure_response()

        district = District.objects.filter(name=request.data.get('old_name')).first()
        if not district:
            return CustomResponse(response={"response": "District not found"}).get_failure_response()

        request.data['name'] = request.data.get('new_name')
        request.data['updated_by'] = user_id
        request.data['updated_at'] = datetime.now()

        serializer = DistrictSerializer(district, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(response=serializer.errors).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def delete(self, request, zone):
        district = District.objects.filter(name=request.data.get('name')).first()
        if not district:
            return CustomResponse(response={"response": "District not found"}).get_failure_response()

        district.delete()
        return CustomResponse(response={"response": "District deleted successfully"}).get_success_response()
