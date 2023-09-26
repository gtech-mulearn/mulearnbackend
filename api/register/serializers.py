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


class UserOrgLinkSerializer(serializers.ModelSerializer):
    user = serializers.CharField(required=False)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=False
    )
    graduation_year = serializers.CharField(required=False)
    organizations = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(), many=True, required=True
    )

    def create(self, validated_data):
        department = validated_data.get("department", None)
        graduation_year = validated_data.get("graduation_year", None)

        is_college = lambda org: org.org_type == OrganizationType.COLLEGE.value

        UserOrganizationLink.objects.bulk_create(
            {
                UserOrganizationLink(
                    user=validated_data["user"],
                    org=org,
                    created_by=validated_data["user"],
                    created_at=DateTimeUtils.get_current_utc_time(),
                    verified=True,
                    department=department if is_college(org) else None,
                    graduation_year=graduation_year if is_college(org) else None,
                )
                for org in validated_data["organizations"]
            }
        )

    class Meta:
        model = UserOrganizationLink
        fields = ["user", "organizations", "verified", "department", "graduation_year"]


class ReferralSerializer(serializers.ModelSerializer):
    user = serializers.CharField(required=False)
    referral = serializers.CharField(required=True)

    class Meta:
        model = UserReferralLink
        fields = ["referral", "user"]

    def validate_referral(self, attrs):
        if referral := User.objects.filter(mu_id=attrs).first():
            return referral

        raise serializers.ValidationError(
            "The provided referrer's μID is not valid. Please double-check and try again."
        )

    def create(self, validated_data):
        validated_data.update(
            {
                "created_by": validated_data["user"],
                "updated_by": validated_data["user"],
            }
        )

        return super().create(validated_data)


class UserSerializer(serializers.ModelSerializer):
    role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), required=False, write_only=True
    )

    def create(self, validated_data):
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

        if level := Level.objects.filter(level_order="1").first():
            UserLvlLink.objects.create(level=level, **additional_values)

        if role:
            additional_values.pop("updated_by")

            UserRoleLink.objects.create(
                role=role,
                verified=role.title == RoleType.STUDENT.value,
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
            "password",
            "role",
        ]


class RegisterSerializer(serializers.Serializer):
    user = UserSerializer()
    organization = UserOrgLinkSerializer(required=False)
    referral = ReferralSerializer(required=False)

    param = serializers.CharField(required=False, allow_null=True)

    def create(self, validated_data):
        with transaction.atomic():
            user = UserSerializer().create(validated_data.pop("user"))

            if organizations := validated_data.pop("organization", None):
                organizations.update({"user": user})
                UserOrgLinkSerializer().create(organizations)

            if referral := validated_data.pop("referral", None):
                referral.update({"user": user})
                ReferralSerializer().create(referral)

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
                

            # invite_code = validated_data.pop("invite_code", None)

            # if invite_code:
            #     mucoin_invite_log = MucoinInviteLog.objects.filter(
            #         invite_code=invite_code
            #     ).first()
            #     if mucoin_invite_log:
            #         referral_provider = User.objects.get(
            #             mu_id=mucoin_invite_log.user.mu_id
            #         )
            #         UserReferralLink.objects.create(
            #             id=uuid4(),
            #             referral=referral_provider,
            #             is_coin=True,
            #             user=user,
            #             created_by=user,
            #             created_at=DateTimeUtils.get_current_utc_time(),
            #             updated_by=user,
            #             updated_at=DateTimeUtils.get_current_utc_time(),
            #         )

        return user

    class Meta:
        model = User
        fields = [
            "user",
            "organization",
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
