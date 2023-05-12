import uuid

from rest_framework.views import APIView
from db.organization import Country, State, District, Zone
from utils.response import CustomResponse
from ..organisation.serializers import CountrySerializer, StateSerializer, DistrictSerializer, ZoneSerializer
from db.user import User
from datetime import datetime


class CountryData(APIView):
    def get(self, request):
        countries = Country.objects.all()
        serializer = CountrySerializer(countries, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    def post(self, request):
        mu_id = request.data.get('mu_id')
        user_id = User.objects.filter(mu_id=mu_id).first().id
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

    def put(self, request):
        mu_id = request.data.get('mu_id')
        user_id = User.objects.filter(mu_id=mu_id).first().id
        if not user_id:
            return CustomResponse(response={"response": "User not found"}).get_failure_response()

        updated_at = datetime.now()

        data = {
            'name': request.data.get('name'),
            'updated_by': user_id,
            'updated_at': updated_at,
        }

        serializer = CountrySerializer(data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(response=serializer.errors).get_failure_response()

    def delete(self, request):
        country = Country.objects.filter(name=request.data.get('name')).first()
        if not country:
            return CustomResponse(response={"response": "Country not found"}).get_failure_response()

        country.delete()
        return CustomResponse(response={"response": "Country deleted successfully"}).get_success_response()


class StateData(APIView):
    def get(self, request, country):
        country_id = Country.objects.filter(name=country).first().id
        states = State.objects.filter(country=country_id)
        serializer = StateSerializer(states, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    def post(self, request):
        mu_id = request.data.get('mu_id')
        user_id = User.objects.filter(mu_id=mu_id).first().id
        country_id = Country.objects.filter(name=request.data.get('country')).first().id
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
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(response=serializer.errors).get_failure_response()

    def put(self, request):
        mu_id = request.data.get('mu_id')
        user_id = User.objects.filter(mu_id=mu_id).first().id

        if not user_id:
            return CustomResponse(response={"response": "User not found"}).get_failure_response()

        if request.data.get('country'):
            country_id = Country.objects.filter(name=request.data.get('country')).first().id
            if not country_id:
                return CustomResponse(response={"response": "Country not found"}).get_failure_response()
            request.data['country'] = country_id

        request.data['updated_by'] = user_id
        request.data['updated_at'] = datetime.now()

        serializer = StateSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(response=serializer.errors).get_failure_response()

    def delete(self, request):
        state = State.objects.filter(name=request.data.get('name')).first()
        if not state:
            return CustomResponse(response={"response": "State not found"}).get_failure_response()

        state.delete()
        return CustomResponse(response={"response": "State deleted successfully"}).get_success_response()


class ZoneData(APIView):
    def get(self, request, state):
        state_id = State.objects.filter(name=state).first().id
        zones = Zone.objects.filter(state=state_id)
        serializer = ZoneSerializer(zones, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    def post(self, request):
        mu_id = request.data.get('mu_id')
        user_id = User.objects.filter(mu_id=mu_id).first().id
        state_id = State.objects.filter(name=request.data.get('state')).first().id
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

    def put(self, request):
        mu_id = request.data.get('mu_id')
        user_id = User.objects.filter(mu_id=mu_id).first().id

        if not user_id:
            return CustomResponse(response={"response": "User not found"}).get_failure_response()

        if request.data.get('state'):
            state_id = State.objects.filter(name=request.data.get('state')).first().id
            if not state_id:
                return CustomResponse(response={"response": "State not found"}).get_failure_response()
            request.data['state'] = state_id

        request.data['updated_by'] = user_id
        request.data['updated_at'] = datetime.now()

        serializer = ZoneSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(response=serializer.errors).get_failure_response()

    def delete(self, request):
        zone = Zone.objects.filter(name=request.data.get('name')).first()
        if not zone:
            return CustomResponse(response={"response": "Zone not found"}).get_failure_response()

        zone.delete()
        return CustomResponse(response={"response": "Zone deleted successfully"}).get_success_response()


class DistrictData(APIView):
    def get(self, request, zone):
        zone_id = Zone.objects.filter(name=zone).first().id
        districts = District.objects.filter(zone=zone_id)
        serializer = DistrictSerializer(districts, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    def post(self, request):
        mu_id = request.data.get('mu_id')
        user_id = User.objects.filter(mu_id=mu_id).first().id
        zone_id = Zone.objects.filter(name=request.data.get('zone')).first().id
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

    def put(self, request):
        mu_id = request.data.get('mu_id')
        user_id = User.objects.filter(mu_id=mu_id).first().id

        if not user_id:
            return CustomResponse(response={"response": "User not found"}).get_failure_response()

        if request.data.get('zone'):
            zone_id = Zone.objects.filter(name=request.data.get('zone')).first().id
            if not zone_id:
                return CustomResponse(response={"response": "Zone not found"}).get_failure_response()
            request.data['zone'] = zone_id

        request.data['updated_by'] = user_id
        request.data['updated_at'] = datetime.now()

        serializer = DistrictSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(response=serializer.errors).get_failure_response()

    def delete(self, request):
        district = District.objects.filter(name=request.data.get('name')).first()
        if not district:
            return CustomResponse(response={"response": "District not found"}).get_failure_response()

        district.delete()
        return CustomResponse(response={"response": "District deleted successfully"}).get_success_response()