from datetime import datetime
from uuid import uuid4

from django.contrib.auth.hashers import make_password
from django.db import transaction
from rest_framework import serializers

from db.organization import Country, State, District, Department, Organization, UserOrganizationLink
from db.task import InterestGroup, TotalKarma, UserIgLink
from db.user import Role, User, UserRoleLink
from utils.types import RoleType
from db.organization import Country, State, Zone


class LearningCircleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "mu_id", "first_name", "last_name", "email", "mobile"]


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "title"]


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "name"]


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ["id", "name"]


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ["id", "name"]


class OrgSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "title"]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "title"]


class AreaOfInterestAPISerializer(serializers.ModelSerializer):
    class Meta:
        model = InterestGroup
        fields = ["id", "name"]


class UserDetailSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(required=True, source="first_name")
    lastName = serializers.CharField(required=True, source="last_name")
    muId = serializers.CharField(required=True, source="mu_id")

    class Meta:
        model = User
        fields = ["id", "muId", "firstName", "lastName", "email"]


class RegisterSerializer(serializers.ModelSerializer):
    role = serializers.CharField(required=False, allow_null=True)
    organizations = serializers.ListField(required=True, allow_null=True)
    dept = serializers.CharField(required=False, allow_null=True)
    yearOfGraduation = serializers.CharField(
        required=False, allow_null=True, max_length=4)
    areaOfInterests = serializers.ListField(required=True, max_length=3)
    firstName = serializers.CharField(
        required=True, source='first_name', max_length=75)
    lastName = serializers.CharField(
        required=False, source='last_name', allow_null=True, max_length=75)
    password = serializers.CharField(
        required=True, max_length=200)

    def create(self, validated_data):
        if validated_data["last_name"] is None:
            full_name = validated_data["first_name"]
        else:
            full_name = validated_data["first_name"] + \
                validated_data["last_name"]
        full_name = full_name.replace(" ", "").lower()[:85]
        mu_id = full_name + "@mulearn"
        counter = 0
        while User.objects.filter(mu_id=mu_id).exists():
            counter += 1
            mu_id = full_name + "-" + str(counter) + "@mulearn"
        role_id = validated_data.pop('role')
        organization_ids = validated_data.pop('organizations')
        dept = validated_data.pop('dept')
        year_of_graduation = validated_data.pop('yearOfGraduation')
        area_of_interests = validated_data.pop('areaOfInterests')
        password = validated_data.pop('password')
        hashed_password = make_password(password)
        user_role_verified = True
        if role_id:
            role = Role.objects.get(id=role_id)
            user_role_verified = role.title == RoleType.STUDENT.value

        with transaction.atomic():
            user = User.objects.create(
                **validated_data, id=uuid4(), mu_id=mu_id, password=hashed_password,
                created_at=datetime.now())
            TotalKarma.objects.create(id=uuid4(), user=user, karma=0, created_by=user, created_at=datetime.now(
            ), updated_by=user, updated_at=datetime.now())

            if role_id:
                UserRoleLink.objects.create(id=uuid4(
                ), user=user, role_id=role_id, created_by=user, created_at=datetime.now(), verified=user_role_verified)
            if organization_ids is not None:
                UserOrganizationLink.objects.bulk_create(
                    [UserOrganizationLink(id=uuid4(), user=user, org_id=org_id, created_by=user,
                                          created_at=datetime.now(), verified=True, department_id=dept,
                                          graduation_year=year_of_graduation) for org_id in organization_ids])
            UserIgLink.objects.bulk_create([UserIgLink(id=uuid4(
            ), user=user, ig_id=ig, created_by=user, created_at=datetime.now()) for ig in area_of_interests])
        return user, password

    class Meta:
        model = User
        fields = ['firstName', 'lastName', 'email', 'mobile', 'gender', 'dob',
                  'role', 'organizations', 'dept', 'yearOfGraduation', 'areaOfInterests', 'password']


class UserSerializer(serializers.ModelSerializer):
    muid = serializers.CharField(source="mu_id")
    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")
    existInGuild = serializers.CharField(source="exist_in_guild")
    joined = serializers.CharField(source="created_at")
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["muid", "firstName", "lastName", "fullname", "fullname", "email", "mobile", "gender", "dob",
                  "active",
                  "existInGuild", "joined", "roles"]

    def get_roles(self, obj):
        roles = []

        for user_role_link in obj.user_role_link_user.all():
            roles.append(user_role_link.role.title)

        return roles


class UserCountrySerializer(serializers.ModelSerializer):
    countryId = serializers.CharField(source='id')
    countryName = serializers.CharField(source='name')
    class Meta:
        model = Country
        fields = ["countryId", "countryName"]


class UserStateSerializer(serializers.ModelSerializer):
    stateId = serializers.CharField(source='id')
    stateName = serializers.CharField(source='name')
    class Meta:
        model = State
        fields = ["stateId", "stateName"]


class UserZoneSerializer(serializers.ModelSerializer):
    zoneId = serializers.CharField(source='id')
    zoneName = serializers.CharField(source='name')
    class Meta:
        model = Zone
        fields = ["zoneId", "zoneName"]


class UserDistrictSerializer(serializers.ModelSerializer):
    districtId = serializers.CharField(source='id')
    districtName = serializers.CharField(source='name')
    class Meta:
        model = District
        fields = ["districtId", "districtName"]


class UserOrganizationSerializer(serializers.ModelSerializer):
    organizationId = serializers.CharField(source='id')
    organizationName = serializers.CharField(source='title')
    class Meta:
        model = Organization
        fields = ["organizationId", "organizationName"]
