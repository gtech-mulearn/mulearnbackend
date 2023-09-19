from uuid import uuid4

from django.contrib.auth.hashers import make_password
from django.db import transaction
from rest_framework import serializers

from api.integrations.kkem.kkem_helper import send_data_to_kkem, decrypt_kkem_data
from api.integrations.kkem.kkem_serializer import KKEMAuthorization
from db.integrations import Integration, IntegrationAuthorization
from db.organization import Country, State, Zone
from db.organization import District, Department, Organization, UserOrganizationLink
from db.task import InterestGroup, TotalKarma, UserIgLink, KarmaActivityLog, TaskList
from db.task import UserLvlLink, Level
from db.user import Role, User, UserRoleLink, UserSettings, UserReferralLink, Socials
from utils.types import IntegrationType, RoleType, TasksTypesHashtag
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


class RegisterSerializer(serializers.ModelSerializer):
    role = serializers.CharField(required=False, allow_null=True)
    organizations = serializers.ListField(required=True, allow_null=True)
    dept = serializers.CharField(required=False, allow_null=True)
    year_of_graduation = serializers.CharField(
        required=False, allow_null=True, max_length=4
    )
    area_of_interests = serializers.ListField(required=True, max_length=3)
    first_name = serializers.CharField(required=True, max_length=75)
    last_name = serializers.CharField(required=False, allow_null=True, max_length=75)
    password = serializers.CharField(required=True, max_length=200)
    referral_id = serializers.CharField(required=False, allow_null=True, max_length=100)
    param = serializers.CharField(required=False, allow_null=True)

    def validate_referral_id(self, value):
        if value:
            if not User.objects.filter(mu_id=value).exists():
                raise serializers.ValidationError("Muid does not exist")
            return value
        return None

    def create(self, validated_data):
        if validated_data["last_name"] is None:
            full_name = validated_data["first_name"]
        else:
            full_name = validated_data["first_name"] + validated_data["last_name"]
        full_name = full_name.replace(" ", "").lower()[:85]
        mu_id = f"{full_name}@mulearn"
        counter = 0
        while User.objects.filter(mu_id=mu_id).exists():
            counter += 1
            mu_id = f"{full_name}-{counter}@mulearn"
        role_id = validated_data.pop("role")
        email = validated_data.pop("email").replace(" ", "")
        organization_ids = validated_data.pop("organizations")
        dept = validated_data.pop("dept")
        year_of_graduation = validated_data.pop("year_of_graduation")
        area_of_interests = validated_data.pop("area_of_interests")
        password = validated_data.pop("password")
        hashed_password = make_password(password)
        referral_id = validated_data.pop("referral_id", None)

        jsid = None
        if param := validated_data.pop("param", None):
            details = decrypt_kkem_data(param)
            jsid = details["jsid"][0]
            dwms_id = details["dwms_id"][0]

            if IntegrationAuthorization.objects.filter(integration_value=jsid).exists():
                raise ValueError(
                    "This KKEM account is already connected to another user"
                )

            integration = Integration.objects.get(name=IntegrationType.KKEM.value)

        referral_provider = None
        user_role_verified = True

        if role_id:
            role = Role.objects.get(id=role_id)
            user_role_verified = role.title == RoleType.STUDENT.value

        if referral_id:
            referral_provider = User.objects.get(mu_id=referral_id)
            task_list = TaskList.objects.filter(
                hashtag=TasksTypesHashtag.REFERRAL.value
            ).first()
            karma_amount = getattr(task_list, "karma", 0)

        with transaction.atomic():
            user = User.objects.create(
                **validated_data,
                id=uuid4(),
                mu_id=mu_id,
                email=email,
                password=hashed_password,
                created_at=DateTimeUtils.get_current_utc_time(),
            )

            TotalKarma.objects.create(
                id=uuid4(),
                user=user,
                karma=0,
                created_by=user,
                created_at=DateTimeUtils.get_current_utc_time(),
                updated_by=user,
                updated_at=DateTimeUtils.get_current_utc_time(),
            )

            Socials.objects.create(
                id=uuid4(),
                user=user,
                created_by=user,
                created_at=DateTimeUtils.get_current_utc_time(),
                updated_by=user,
                updated_at=DateTimeUtils.get_current_utc_time(),
            )

            if role_id:
                UserRoleLink.objects.create(
                    id=uuid4(),
                    user=user,
                    role_id=role_id,
                    created_by=user,
                    created_at=DateTimeUtils.get_current_utc_time(),
                    verified=user_role_verified,
                )

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

            UserIgLink.objects.bulk_create(
                [
                    UserIgLink(
                        id=uuid4(),
                        user=user,
                        ig_id=ig,
                        created_by=user,
                        created_at=DateTimeUtils.get_current_utc_time(),
                    )
                    for ig in area_of_interests
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

            UserSettings.objects.create(
                id=uuid4(),
                user=user,
                is_public=0,
                created_by=user,
                created_at=DateTimeUtils.get_current_utc_time(),
                updated_by=user,
                updated_at=DateTimeUtils.get_current_utc_time(),
            )

            if referral_id:
                UserReferralLink.objects.create(
                    id=uuid4(),
                    referral=referral_provider,
                    user=user,
                    created_by=user,
                    created_at=DateTimeUtils.get_current_utc_time(),
                    updated_by=user,
                    updated_at=DateTimeUtils.get_current_utc_time(),
                )
                KarmaActivityLog.objects.create(
                    id=uuid4(),
                    karma=karma_amount,
                    task=task_list,
                    created_by=user,
                    user=referral_provider,
                    created_at=DateTimeUtils.get_current_utc_time(),
                    appraiser_approved=False,
                    peer_approved=True,
                    appraiser_approved_by=user,
                    peer_approved_by=user,
                    updated_by=user,
                    updated_at=DateTimeUtils.get_current_utc_time(),
                )

                referrer_karma = TotalKarma.objects.filter(
                    user=referral_provider
                ).first()

                referrer_karma.karma += karma_amount
                referrer_karma.updated_at = DateTimeUtils.get_current_utc_time()
                referrer_karma.updated_by = user
                referrer_karma.save()

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

        return user, password

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "mobile",
            "gender",
            "dob",
            "role",
            "organizations",
            "dept",
            "year_of_graduation",
            "area_of_interests",
            "password",
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


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"


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
        model = TotalKarma
        fields = ["karma", "updated_by"]


class ReferralSerializer(serializers.ModelSerializer):
    referral = serializers.CharField(source="referral.mu_id")
    user = serializers.CharField(required=False)

    karma_activity_log = KarmaActivityLogSerializer(required=False)
    total_karma = TotalKarmaSerializer(required=False)

    class Meta:
        model = UserReferralLink
        fields = ["referral", "user", "karma_activity_log", "total_karma"]

    def create(self, validated_data):
        creation = {
            "created_by": validated_data["user"],
            "updated_by": validated_data["user"],
        }

        validated_data.update(creation)
        validated_data["referral"] = User.objects.get(
            mu_id=validated_data["referral"]["mu_id"]
        )
        user_referral_link = super().create(validated_data)

        validated_data["karma_activity_log"]["user"] = user_referral_link.referral
        validated_data["karma_activity_log"]["created_by"] = user_referral_link.user
        validated_data["karma_activity_log"]["updated_by"] = user_referral_link.user

        karma_activity_log_serializer = KarmaActivityLogSerializer(data=validated_data)

        if not karma_activity_log_serializer.is_valid():
            return serializers.ValidationError(karma_activity_log_serializer.errors)

        karma_activity_log_serializer.save()

        referrer_karma = TotalKarma.objects.filter(
            user=user_referral_link.referral
        ).first()

        total_karma_serializer = TotalKarmaSerializer(
            referrer_karma, data=validated_data
        )

        if not total_karma_serializer.is_valid():
            return serializers.ValidationError(total_karma_serializer.errors)

        total_karma_serializer.save()

        return user_referral_link


class RegisterNewSerializer(serializers.Serializer):
    user = UserSerializer()
    dwms = KKEMAuthorization(required=False)
    referral = ReferralSerializer(required=False)

    class Meta:
        fields = ["user", "dwms", "referral"]

    def create(self, validated_data):
        with transaction.atomic():
            # Save user first
            user_data = validated_data.pop("user")
            serializer_user = UserSerializer(data=user_data)
            if not serializer_user.is_valid():
                raise serializers.ValidationError(serializer_user.errors)
            user = serializer_user.save()

            # After saving the user and getting mu_id from the database
            # update the dwms data if it exists
            if "dwms" in validated_data:
                dwms_data = validated_data.pop("dwms")
                dwms_data["emailOrMuid"] = user.mu_id
                dwms_data["verified"] = True

                # Now validate and save dwms data with the updated values
                serializer_dwms = KKEMAuthorization(data=dwms_data)
                if not serializer_dwms.is_valid():
                    raise serializers.ValidationError(serializer_dwms.errors)
                serializer_dwms.save()

            if "referral" in validated_data:
                referral_data = validated_data.pop("referral")
                referral_data["user"] = user.id

                # Now validate and save dwms data with the updated values
                serializer_referral = ReferralSerializer(data=referral_data)
                if not serializer_referral.is_valid():
                    raise serializers.ValidationError(serializer_referral.errors)
                serializer_referral.save()

            # self.handle_referral(validated_data, user)

            # TotalKarma.objects.create(
            #     id=uuid4(),
            #     user=user,
            #     karma=0,
            #     created_by=user,
            #     created_at=DateTimeUtils.get_current_utc_time(),
            #     updated_by=user,
            #     updated_at=DateTimeUtils.get_current_utc_time(),
            # )

            # Socials.objects.create(
            #     id=uuid4(),
            #     user=user,
            #     created_by=user,
            #     created_at=DateTimeUtils.get_current_utc_time(),
            #     updated_by=user,
            #     updated_at=DateTimeUtils.get_current_utc_time(),
            # )

            # UserSettings.objects.create(
            #     id=uuid4(),
            #     user=user,
            #     is_public=0,
            #     created_by=user,
            #     created_at=DateTimeUtils.get_current_utc_time(),
            #     updated_by=user,
            #     updated_at=DateTimeUtils.get_current_utc_time(),
            # )

        return user, validated_data["password"]
