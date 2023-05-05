from datetime import datetime
from uuid import uuid4

from django.db import transaction
from rest_framework import serializers

from utils.types import RoleType
from django.contrib.auth.hashers import make_password
from db.organization import Department, Organization, UserOrganizationLink
from db.task import InterestGroup, TotalKarma, UserIgLink
from db.user import Role, User, UserRoleLink


class LearningCircleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "mu_id", "first_name", "last_name", "email", "mobile"]


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "title"]


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
        required=True,max_length=200)

    def create(self, validated_data):
        if validated_data["last_name"] is None:
            full_name = validated_data["first_name"]
        else:
            full_name = validated_data["first_name"] + validated_data["last_name"]
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
                **validated_data, id=uuid4(), mu_id=mu_id,password=hashed_password,
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
        return user,password

    class Meta:
        model = User
        fields = ['firstName', 'lastName', 'email', 'mobile', 'gender', 'dob',
                  'role', 'organizations', 'dept', 'yearOfGraduation', 'areaOfInterests','password']
