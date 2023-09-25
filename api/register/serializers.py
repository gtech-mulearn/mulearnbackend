from uuid import uuid4

from django.contrib.auth.hashers import make_password
from django.db import transaction
from rest_framework import serializers

from api.integrations.kkem.kkem_helper import send_data_to_kkem, decrypt_kkem_data
from db.integrations import Integration, IntegrationAuthorization
from db.organization import Country, State, Zone
from db.organization import District, Department, Organization, UserOrganizationLink
from db.task import (
    InterestGroup,
    Wallet,
    UserIgLink,
    TaskList,
    MucoinInviteLog,
    KarmaActivityLog,
)
from db.task import UserLvlLink, Level
from db.user import Role, User, UserRoleLink, UserSettings, UserReferralLink, Socials
from utils.types import IntegrationType, OrganizationType, RoleType, TasksTypesHashtag
from utils.utils import DateTimeUtils

from . import register_helper


class LearningCircleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "mu_id", "first_name", "last_name", "email", "mobile"]


class BaseSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()


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
    role = serializers.SerializerMethodField()
    fullname = serializers.SerializerMethodField()

    def get_fullname(self, obj):
        return obj.fullname

    def get_role(self, obj):
        role_link = obj.user_role_link_user.filter(
            role__title__in=[RoleType.MENTOR.value, RoleType.ENABLER.value]
        ).first()
        return role_link.role.title if role_link else None

    class Meta:
        model = User
        fields = [
            "id",
            "mu_id",
            "first_name",
            "last_name",
            "email",
            "role",
            "fullname",
        ]


class UserSerializer(serializers.ModelSerializer):
    role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), required=False, write_only=True
    )

    def create(self, validated_data):
        """
        The `create` function generates a unique `mu_id` for a user, hashes their password, creates related
        objects, and assigns a role to the user.

        :param validated_data: The `validated_data` parameter is a dictionary that contains the validated
        data for creating a new user. It typically includes fields such as `first_name`, `last_name`,
        `password`, and `role`
        :return: The `create` method returns the `user` object.
        """
        role = validated_data.pop("role", None)
        
        
        validated_data["mu_id"] = register_helper.generate_mu_id(
            validated_data["first_name"], validated_data["last_name"]
        )
        password = validated_data.pop("password")
        hashed_password = make_password(password)
        validated_data["password"] = hashed_password


        user = super().create(validated_data)

        additional_values = {"user": user, "created_by": user, "updated_by": user}

        Wallet.objects.create(**additional_values)
        Socials.objects.create(**additional_values)
        UserSettings.objects.create(**additional_values)

        if role:
            additional_values.pop("updated_by")
            
            UserRoleLink.objects.create(
                role=role,
                verified=role == RoleType.STUDENT.value,
                **additional_values,
            )

        return user

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "mobile",
            "gender",
            "dob",
            "password",
            "role",
        ]


class RegisterSerializer(serializers.Serializer):
    user = UserSerializer()

    organizations = serializers.ListField(required=True, allow_null=True)
    dept = serializers.CharField(required=False, allow_null=True)
    year_of_graduation = serializers.CharField(
        required=False, allow_null=True, max_length=4
    )
    referral_id = serializers.CharField(required=False, allow_null=True, max_length=100)
    param = serializers.CharField(required=False, allow_null=True)

    def validate_referral_id(self, value):
        if value:
            if not User.objects.filter(mu_id=value).exists():
                raise serializers.ValidationError("Muid does not exist")
            return value
        return None

    def create(self, validated_data):
        with transaction.atomic():
            user = UserSerializer().create(validated_data.pop("user"))

            organization_ids = validated_data.pop("organizations")
            dept = validated_data.pop("dept", None)
            year_of_graduation = validated_data.pop("year_of_graduation", None)

            referral_id = validated_data.pop("referral_id", None)
            invite_code = validated_data.pop("invite_code", None)

            jsid = None
            if param := validated_data.pop("param", None):
                details = decrypt_kkem_data(param)
                jsid = details["jsid"][0]
                dwms_id = details["dwms_id"][0]

                if IntegrationAuthorization.objects.filter(
                    integration_value=jsid
                ).exists():
                    raise ValueError(
                        "This KKEM account is already connected to another user"
                    )

                integration = Integration.objects.get(name=IntegrationType.KKEM.value)

            referral_provider = None

            if referral_id:
                referral_provider = User.objects.get(mu_id=referral_id)
                task_list = TaskList.objects.filter(
                    hashtag=TasksTypesHashtag.REFERRAL.value
                ).first()
                karma_amount = getattr(task_list, "karma", 0)

            if organization_ids is not None:
                UserOrganizationLink.objects.bulk_create(
                    [
                        UserOrganizationLink(
                            id=uuid4(),
                            user=user,
                            org_id=org_id,
                            created_by=user,
                            created_at=DateTimeUtils.get_current_utc_time(),
                            verified=True,
                            department_id=dept,
                            graduation_year=year_of_graduation,
                        )
                        for org_id in organization_ids
                    ]
                )

            if level := Level.objects.filter(level_order="1").first():
                UserLvlLink.objects.create(
                    id=uuid4(),
                    user=user,
                    level=level,
                    updated_by=user,
                    updated_at=DateTimeUtils.get_current_utc_time(),
                    created_by=user,
                    created_at=DateTimeUtils.get_current_utc_time(),
                )

            if referral_id:
                UserReferralLink.objects.create(
                    id=uuid4(),
                    referral=referral_provider,
                    is_coin=False,
                    user=user,
                    created_by=user,
                    created_at=DateTimeUtils.get_current_utc_time(),
                    updated_by=user,
                    updated_at=DateTimeUtils.get_current_utc_time(),
                )

            if invite_code:
                mucoin_invite_log = MucoinInviteLog.objects.filter(
                    invite_code=invite_code
                ).first()
                if mucoin_invite_log:
                    referral_provider = User.objects.get(
                        mu_id=mucoin_invite_log.user.mu_id
                    )
                    UserReferralLink.objects.create(
                        id=uuid4(),
                        referral=referral_provider,
                        is_coin=True,
                        user=user,
                        created_by=user,
                        created_at=DateTimeUtils.get_current_utc_time(),
                        updated_by=user,
                        updated_at=DateTimeUtils.get_current_utc_time(),
                    )

            if jsid:
                kkem_link = IntegrationAuthorization.objects.create(
                    id=uuid4(),
                    user=user,
                    integration=integration,
                    integration_value=jsid,
                    additional_field=dwms_id,
                    verified=True,
                    created_at=DateTimeUtils.get_current_utc_time(),
                    updated_at=DateTimeUtils.get_current_utc_time(),
                )

                send_data_to_kkem(kkem_link)

        return user

    class Meta:
        model = User
        fields = [
            "user",
            "organizations",
            "dept",
            "year_of_graduation",
            "area_of_interests",
            "referral_id",
            "param",
        ]


class UserCountrySerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source="name")

    class Meta:
        model = Country
        fields = ["country_name"]


class UserStateSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source="name")

    class Meta:
        model = State
        fields = ["state_name"]


class UserZoneSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source="name")

    class Meta:
        model = Zone
        fields = ["zone_name"]


class UserOrgLinkSerializer(serializers.ModelSerializer):
    org = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(), many=True, required=True
    )
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), many=False, required=False
    )
    graduation_year = serializers.DateField(
        required=False, allow_null=True, format="%Y"
    )

    def create(self, validated_data):
        organizations = Organization.filter.objects.filter(id__in=validated_data["org"])
        # user = User.objects.get(id=validated_data["user"])
        Organization.objects.bulk_create(
            {
                UserOrganizationLink(
                    user=validated_data["user"],
                    org=org,
                    created_by=validated_data["user"],
                    created_at=DateTimeUtils.get_current_utc_time(),
                    verified=True,
                    department=validated_data["department"]
                    if org.type == OrganizationType.COLLEGE.value
                    else None,
                    graduation_year=validated_data["graduation_year"]
                    if org.type == OrganizationType.COLLEGE.value
                    else None,
                )
                for org in organizations
            }
        )

    class Meta:
        model = UserOrganizationLink
        fields = ["user", "org", "verified", "department", "graduation_year"]


class UserRoleLinkSerializer(serializers.ModelSerializer):
    role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), many=True, required=True
    )
    user = serializers.CharField(required=False)

    def create(self, validated_data):
        organizations = Organization.filter.objects.filter(id__in=validated_data["org"])
        # user = User.objects.get(id=validated_data["user"])
        Organization.objects.bulk_create(
            {
                UserOrganizationLink(
                    user=validated_data["user"],
                    org=org,
                    created_by=validated_data["user"],
                    created_at=DateTimeUtils.get_current_utc_time(),
                    verified=True,
                    department=validated_data["department"]
                    if org.type == OrganizationType.COLLEGE.value
                    else None,
                    graduation_year=validated_data["graduation_year"]
                    if org.type == OrganizationType.COLLEGE.value
                    else None,
                )
                for org in organizations
            }
        )

    class Meta:
        model = UserOrganizationLink
        fields = ["user", "org", "verified", "department", "graduation_year"]


class KarmaActivityLogSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        validated_data["appraiser_approved_by"] = validated_data[
            "peer_approved_by"
        ] = validated_data["created_by"]

        validated_data["appraiser_approved"] = False
        validated_data["peer_approved"] = True

        task_list = TaskList.objects.filter(
            hashtag=TasksTypesHashtag.REFERRAL.value
        ).first()

        karma_amount = getattr(task_list, "karma", 0)

        validated_data["karma"] = karma_amount
        validated_data["task"] = task_list

        super().create(validated_data)

    class Meta:
        model = KarmaActivityLog
        fields = ["created_by", "user", "updated_by"]


class TotalKarmaSerializer(serializers.ModelSerializer):
    def update(self, instance, validated_data):
        validated_data["karma"] = validated_data["karma"] + instance.karma
        return super().update(instance, validated_data)

    class Meta:
        model = Wallet
        fields = ["karma", "updated_by"]


class ReferralSerializer(serializers.ModelSerializer):
    referral = serializers.CharField(source="referral.mu_id")
    user = serializers.CharField(source="user.mu_id")

    karma_activity_log = KarmaActivityLogSerializer(required=False)
    total_karma = TotalKarmaSerializer(required=False)

    def validate(self, attrs):
        values = super().validate(attrs)
        values["referral"] = User.objects.get(mu_id=values["referral"]["mu_id"]).pk
        values["user"] = User.objects.get(mu_id=values["user"]["mu_id"]).pk
        return values

    class Meta:
        model = UserReferralLink
        fields = ["referral", "user", "karma_activity_log", "total_karma"]

    def create(self, validated_data):
        creation = {
            "created_by": validated_data["user"],
            "updated_by": validated_data["user"],
        }

        validated_data.update(creation)

        user_referral_link = super().create(validated_data)

        validated_data["karma_activity_log"]["user"] = user_referral_link.referral
        validated_data["karma_activity_log"]["created_by"] = user_referral_link.user
        validated_data["karma_activity_log"]["updated_by"] = user_referral_link.user

        karma_activity_log_serializer = KarmaActivityLogSerializer(data=validated_data)

        if not karma_activity_log_serializer.is_valid():
            return serializers.ValidationError(karma_activity_log_serializer.errors)

        karma_activity_log_serializer.save()

        referrer_karma = Wallet.objects.filter(user=user_referral_link.referral).first()

        total_karma_serializer = TotalKarmaSerializer(
            referrer_karma, data=validated_data
        )

        if not total_karma_serializer.is_valid():
            return serializers.ValidationError(total_karma_serializer.errors)

        total_karma_serializer.save()

        return user_referral_link
