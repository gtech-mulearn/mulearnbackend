import uuid
from django.contrib.auth.hashers import make_password
from django.db import transaction
from rest_framework import serializers

from api.integrations.kkem.kkem_helper import decrypt_kkem_data, send_data_to_kkem
from db.integrations import Integration, IntegrationAuthorization
from db.organization import (
    Country,
    Department,
    District,
    Organization,
    State,
    UserOrganizationLink,
    Zone,
)
from db.task import (
    InterestGroup,
    Level,
    MucoinInviteLog,
    UserIgLink,
    UserLvlLink,
    Wallet,
)
from db.user import (
    Role,
    Socials,
    User,
    UserMentor,
    UserReferralLink,
    UserRoleLink,
    UserSettings,
    UserInterests,
)
from utils.exception import CustomException
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils
from . import register_helper


class LearningCircleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "muid", "full_name", "email", "mobile"]


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

    def get_role(self, obj):
        role_link = obj.user_role_link_user.filter(
            role__title__in=[RoleType.MENTOR.value, RoleType.ENABLER.value]
        ).first()
        return role_link.role.title if role_link else None

    class Meta:
        model = User
        fields = [
            "id",
            "muid",
            "email",
            "role",
            "full_name",
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
        fields = ["user", "organizations", "department", "graduation_year"]


class MentorSerializer(serializers.ModelSerializer):
    user = serializers.CharField(required=False)
    about = serializers.CharField(required=False)
    reason = serializers.CharField(required=False)
    hours = serializers.IntegerField(required=False)

    def create(self, validated_data):
        about = validated_data.get("about", None)
        reason = validated_data.get("reason", None)
        hours = validated_data.get("hours", None)

        UserMentor.objects.create(
            user=validated_data["user"],
            about=about,
            reason=reason,
            hours=hours,
            created_by=validated_data["user"],
            created_at=DateTimeUtils.get_current_utc_time(),
            updated_by=validated_data["user"],
            updated_at=DateTimeUtils.get_current_utc_time(),
        )

    class Meta:
        model = UserMentor
        fields = [
            "user",
            "about",
            "reason",
            "hours",
        ]


class ReferralSerializer(serializers.ModelSerializer):
    user = serializers.CharField(required=False)
    muid = serializers.CharField(required=False)
    invite_code = serializers.CharField(required=False)

    class Meta:
        model = UserReferralLink
        fields = ["muid", "user", "invite_code", "is_coin"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if "muid" in data:
            data["muid"] = instance.get("muid").muid
        return data

    def validate(self, attrs):
        if not attrs.get("muid", None) and not attrs.get("invite_code", None):
            raise serializers.ValidationError(
                "Please provide either a referral μID or an invite code"
            )
        return super().validate(attrs)

    def validate_muid(self, muid):
        if referral := User.objects.filter(muid=muid).first():
            return referral

        raise serializers.ValidationError(
            "The provided referrer's μID is not valid. Please double-check and try again."
        )

    def validate_invite_code(self, invite_code):
        try:
            return MucoinInviteLog.objects.filter(invite_code=invite_code).first().user
        except MucoinInviteLog.DoesNotExist as e:
            raise serializers.ValidationError(
                "The provided invite code is not valid."
            ) from e

    def create(self, validated_data):
        referral = validated_data.get("invite_code", None) or validated_data.get(
            "muid", None
        )

        validated_data.update(
            {
                "created_by": validated_data["user"],
                "updated_by": validated_data["user"],
                "referral": referral,
                "is_coin": "invite_code" in validated_data,
            }
        )
        validated_data.pop("invite_code", None) or validated_data.pop("muid", None)
        return super().create(validated_data)


class IntegrationSerializer(serializers.Serializer):
    param = serializers.CharField()
    title = serializers.CharField()

    def validate_param(self, param):
        try:
            details = decrypt_kkem_data(param)
            jsid = details["jsid"][0]
            dwms_id = details["dwms_id"][0]

            if IntegrationAuthorization.objects.filter(integration_value=jsid).exists():
                raise CustomException(
                    "This KKEM account is already connected to another user"
                )

            return {"jsid": jsid, "dwms_id": dwms_id}
        except Exception as e:
            raise serializers.ValidationError(str(e)) from e

    def validate_title(self, integration):
        try:
            return Integration.objects.get(name=integration)
        except Exception as e:
            raise serializers.ValidationError(str(e)) from e

    def create(self, validated_data):
        kkem_link = IntegrationAuthorization.objects.create(
            user=validated_data["user"],
            integration=validated_data["title"],
            integration_value=validated_data["param"]["jsid"],
            additional_field=validated_data["param"]["dwms_id"],
            verified=True,
        )

        send_data_to_kkem(kkem_link)
        return kkem_link


class UserSerializer(serializers.ModelSerializer):
    role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), required=False, write_only=True
    )
    area_of_interest = serializers.PrimaryKeyRelatedField(
        queryset=InterestGroup.objects.all(), many=True, required=False
    )

    def create(self, validated_data):
        role = validated_data.pop("role", None)
        area_of_interest = validated_data.pop("area_of_interest", None)

        validated_data["muid"] = register_helper.generate_muid(
            validated_data["full_name"]
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

        if area_of_interest:
            UserIgLink.objects.bulk_create(
                {
                    UserIgLink(
                        user=user,
                        ig=ig,
                        created_by=user,
                        created_at=DateTimeUtils.get_current_utc_time(),
                    )
                    for ig in area_of_interest
                }
            )

        return user

    class Meta:
        model = User
        fields = [
            "full_name",
            "email",
            # "mobile",
            "password",
            "dob",
            "gender",
            "role",
            "district",
            "area_of_interest",
        ]


class RegisterSerializer(serializers.Serializer):
    user = UserSerializer()
    organization = UserOrgLinkSerializer(required=False)
    referral = ReferralSerializer(required=False)
    integration = IntegrationSerializer(required=False)
    mentor = MentorSerializer(required=False)

    def create(self, validated_data):
        with transaction.atomic():
            user = UserSerializer().create(validated_data.pop("user"))

            if organizations := validated_data.pop("organization", None):
                organizations.update({"user": user})
                UserOrgLinkSerializer().create(organizations)

            if referral := validated_data.pop("referral", None):
                referral.update({"user": user})
                ReferralSerializer().create(referral)

            if integration := validated_data.pop("integration", None):
                integration.update({"user": user})
                IntegrationSerializer().create(integration)

            if mentor := validated_data.pop("mentor", None):
                mentor["user"] = user
                MentorSerializer().create(mentor)

        return user

    class Meta:
        model = User
        fields = [
            "user",
            "organization",
            "referral",
            "param",
            "mentor",
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


class LocationSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()

    class Meta:
        model = District
        fields = ("id", "location")

    def get_location(self, obj):
        return f"{obj.name}, {obj.zone.state.name}, {obj.zone.state.country.name}"


class UserInterestSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    user = serializers.CharField(read_only=True)
    choosen_interests = serializers.JSONField()
    other_interests = serializers.JSONField(required=False)
    choosen_endgoals = serializers.JSONField()
    other_endgoals = serializers.JSONField(required=False)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        validated_data["created_at"] = validated_data["updated_at"] = (
            DateTimeUtils.get_current_utc_time()
        )
        if user := self.context.get("user"):
            validated_data["user"] = user
        else:
            return serializers.ValidationError("User not found")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("choosen_interests", None):
            instance.choosen_interests = validated_data.get("choosen_interests", [])
        if validated_data.get("other_interests", None):
            instance.other_interests = validated_data.get("other_interests", [])
        if validated_data.get("choosen_endgoals", None):
            instance.choosen_endgoals = validated_data.get("choosen_endgoals", [])
        if validated_data.get("other_endgoals", None):
            instance.other_endgoals = validated_data.get("other_endgoals", [])
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        return instance.save()

    def validate_choosen_interests(self, interests):
        if not all(
            interest in ("maker", "software", "creative", "manager", "others")
            for interest in interests
        ):
            raise serializers.ValidationError("Invalid interests selected.")
        return list(set(interests))

    def validate_choosen_endgoals(self, end_goals):
        if not all(
            goal
            in (
                "job",
                "higher_education",
                "gig_work",
                "entrepreneurship",
                "others",
            )
            for goal in end_goals
        ):
            raise serializers.ValidationError("Invalid end goals selected.")
        return list(set(end_goals))

    class Meta:
        model = UserInterests
        fields = [
            "id",
            "user",
            "choosen_interests",
            "other_interests",
            "choosen_endgoals",
            "other_endgoals",
            "created_at",
            "updated_at",
        ]
