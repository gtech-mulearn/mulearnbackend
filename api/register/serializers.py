from uuid import uuid4

from django.contrib.auth.hashers import make_password
from django.db import transaction
from rest_framework import serializers

from db.organization import Country, State, Zone
from db.organization import District, Department, Organization, UserOrganizationLink
from db.task import InterestGroup, TotalKarma, UserIgLink, KarmaActivityLog, TaskList
from db.task import UserLvlLink, Level
from db.user import Role, User, UserRoleLink, UserSettings, UserReferralLink
from utils.types import RoleType, TasksTypesHashtag
from utils.utils import DateTimeUtils


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
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    mu_id = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ["id", "mu_id", "first_name", "last_name", "email"]


class RegisterSerializer(serializers.ModelSerializer):
    role = serializers.CharField(required=False, allow_null=True)
    organizations = serializers.ListField(required=True, allow_null=True)
    dept = serializers.CharField(required=False, allow_null=True)
    year_of_graduation = serializers.CharField(
        required=False, allow_null=True, max_length=4)
    area_of_interests = serializers.ListField(required=True, max_length=3)
    first_name = serializers.CharField(
        required=True, max_length=75)
    last_name = serializers.CharField(
        required=False, allow_null=True, max_length=75)
    password = serializers.CharField(
        required=True, max_length=200)
    referral_id = serializers.CharField(required=False, allow_null=True, max_length=100)

    def create(self, validated_data):
        if validated_data["last_name"] is None:
            full_name = validated_data["first_name"]
        else:
            full_name = validated_data["first_name"] + \
                            validated_data["last_name"]
        full_name = full_name.replace(" ", "").lower()[:85]
        mu_id = f"{full_name}@mulearn"
        counter = 0
        while User.objects.filter(mu_id=mu_id).exists():
            counter += 1
            mu_id = f"{full_name}-{counter}@mulearn"
        role_id = validated_data.pop('role')
        organization_ids = validated_data.pop('organizations')
        dept = validated_data.pop('dept')
        year_of_graduation = validated_data.pop('year_of_graduation')
        area_of_interests = validated_data.pop('area_of_interests')
        password = validated_data.pop('password')
        hashed_password = make_password(password)
        referral_id = validated_data.pop('referral_id')
        referral_provider = None

        user_role_verified = True
        if role_id:
            role = Role.objects.get(id=role_id)
            user_role_verified = role.title == RoleType.STUDENT.value

        if referral_id:
            if not User.objects.filter(mu_id=referral_id).exists():
                raise serializers.ValidationError("Muid does not exist")

            referral_provider = User.objects.get(mu_id=referral_id)
            task_list = TaskList.objects.filter(hashtag=TasksTypesHashtag.REFERRAL.value).first()
            karma_amount = task_list.karma
        with transaction.atomic():

            user = User.objects.create(
                **validated_data, id=uuid4(), mu_id=mu_id, password=hashed_password,
                created_at=DateTimeUtils.get_current_utc_time())

            TotalKarma.objects.create(id=uuid4(), user=user, karma=0, created_by=user,
                                      created_at=DateTimeUtils.get_current_utc_time(), updated_by=user,
                                      updated_at=DateTimeUtils.get_current_utc_time())

            if role_id:
                UserRoleLink.objects.create(id=uuid4(
                ), user=user, role_id=role_id, created_by=user, created_at=DateTimeUtils.get_current_utc_time(),
                    verified=user_role_verified)

            if organization_ids is not None:
                UserOrganizationLink.objects.bulk_create(
                    [UserOrganizationLink(id=uuid4(), user=user, org_id=org_id, created_by=user,
                                          created_at=DateTimeUtils.get_current_utc_time(), verified=True,
                                          department_id=dept,
                                          graduation_year=year_of_graduation) for org_id in organization_ids])

            UserIgLink.objects.bulk_create([UserIgLink(id=uuid4(), user=user, ig_id=ig, created_by=user,
                                                       created_at=DateTimeUtils.get_current_utc_time()) for ig in
                                            area_of_interests])

            level = Level.objects.filter(level_order='1').first()
            if level:
                UserLvlLink.objects.create(id=uuid4(), user=user, level=level, updated_by=user,
                                           updated_at=DateTimeUtils.get_current_utc_time(), created_by=user,
                                           created_at=DateTimeUtils.get_current_utc_time())

            UserSettings.objects.create(id=uuid4(), user=user, is_public=0, created_by=user,
                                        created_at=DateTimeUtils.get_current_utc_time(), updated_by=user,
                                        updated_at=DateTimeUtils.get_current_utc_time())

            if referral_id:
                UserReferralLink.objects.create(id=uuid4(), referral=referral_provider, user=user,
                                                created_by=user,
                                                created_at=DateTimeUtils.get_current_utc_time(),
                                                updated_by=user,
                                                updated_at=DateTimeUtils.get_current_utc_time())
                KarmaActivityLog.objects.create(
                    id=uuid4(), karma=karma_amount, task=task_list, created_by=user,
                    user=referral_provider,
                    created_at=DateTimeUtils.get_current_utc_time(), appraiser_approved=True, peer_approved=True,
                    appraiser_approved_by=user, peer_approved_by=user,
                    updated_by=user, updated_at=DateTimeUtils.get_current_utc_time())

                referrer_karma = TotalKarma.objects.filter(user=referral_provider).first()
                referrer_karma.karma = referrer_karma.karma + karma_amount
                referrer_karma.updated_at = DateTimeUtils.get_current_utc_time()
                referrer_karma.updated_by = user
                referrer_karma.save()

        return user, password

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'mobile', 'gender', 'dob', 'role', 'organizations', 'dept',
                  'year_of_graduation', 'area_of_interests', 'password', 'referral_id']


class UserCountrySerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source='name')

    class Meta:
        model = Country
        fields = ["country_name"]


class UserStateSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source='name')

    class Meta:
        model = State
        fields = ["state_name"]


class UserZoneSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source='name')

    class Meta:
        model = Zone
        fields = ["zone_name"]
