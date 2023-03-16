from datetime import datetime
from uuid import uuid4
from rest_framework import serializers
from organization.models import Country, Department, Organization, UserOrganizationLink
from portal.models import Portal
from task.models import InterestGroup, TotalKarma, UserIgLink
from user.models import Role, User, UserRoleLink
from django.db import transaction


# class CountrySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Country
#         fields = '__all__'


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'title']


class OrgSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'title']


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'title']


class AreaOfInterstAPISerializer(serializers.ModelSerializer):
    class Meta:
        model = InterestGroup
        fields = ['id', 'name']


class UserDetailSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(required=True, source='first_name')
    lastName = serializers.CharField(required=True, source='last_name')
    muId = serializers.CharField(required=True, source='mu_id')

    class Meta:
        model = User
        fields = ['id', 'muId', 'firstName', 'lastName', 'email']


class RegisterSerializer(serializers.ModelSerializer):
    role = serializers.CharField(required=True)
    organization = serializers.CharField(required=True)
    dept = serializers.CharField(required=False, allow_null=True)
    yearOfGraduation = serializers.CharField(required=False, allow_null=True)
    areaOfInterest = serializers.ListField(required=True)
    firstName = serializers.CharField(required=True, source='first_name')
    lastName = serializers.CharField(
        required=False, source='last_name', allow_null=True)

    def create(self, validated_data):
        if validated_data['last_name'] is None:
            full_name = validated_data['first_name']
        else:
            full_name = validated_data['first_name'] + \
                validated_data['last_name']
        full_name = full_name.replace(" ", "").lower()[:12]
        mu_id = full_name + "@mulearn"
        counter = 0
        while User.objects.filter(mu_id=mu_id).exists():
            counter += 1
            mu_id = full_name.replace(
                " ", "").lower() + "-" + str(counter) + "@muearn"
        role = validated_data.pop('role')
        organization = validated_data.pop('organization')
        dept = validated_data.pop('dept')
        year_of_graduation = validated_data.pop('yearOfGraduation')
        area_of_interest = validated_data.pop('areaOfInterest')
        with transaction.atomic():
            user = User.objects.create(
                **validated_data, id=uuid4(), mu_id=mu_id, discord_id=self.context['request'].auth.get('id', None), created_at=datetime.now())
            TotalKarma.objects.create(id=uuid4(), user=user, karma=0, created_by=user, created_at=datetime.now(
            ), updated_by=user, updated_at=datetime.now())
            UserRoleLink.objects.create(id=uuid4(
            ), user=user, role_id=role, created_by=user, created_at=datetime.now(), verified=1)
            UserOrganizationLink.objects.create(id=uuid4(), user=user, org_id=organization, created_by=user,
                                                created_at=datetime.now(), verified=1, department_id=dept, graduation_yer=year_of_graduation)
            UserIgLink.objects.bulk_create([UserIgLink(id=uuid4(
            ), user=user, ig_id=ig, created_by=user, created_at=datetime.now()) for ig in area_of_interest])
        return user

    class Meta:
        model = User
        fields = ['firstName', 'lastName', 'email', 'mobile', 'gender', 'dob',
                  'role', 'organization', 'dept', 'yearOfGraduation', 'areaOfInterest']
