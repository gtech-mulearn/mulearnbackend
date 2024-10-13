import uuid

from decouple import config as decouple_config
from django.db import transaction
from rest_framework import serializers

from db.organization import Department, Organization, UserOrganizationLink
from db.task import UserIgLink
from db.user import Role, User, UserRoleLink
from utils.permission import JWTUtils
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils
from db.user import DynamicRole, DynamicUser
from db.user import UserInterests

BE_DOMAIN_NAME = decouple_config("BE_DOMAIN_NAME")


class UserDashboardSerializer(serializers.ModelSerializer):
    karma = serializers.IntegerField(source="wallet_user.karma", default=None)
    level = serializers.CharField(source="user_lvl_link_user.level.name", default=None)

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "muid",
            "discord_id",
            "email",
            "mobile",
            "created_at",
            "karma",
            "level",
        ]


class UserSerializer(serializers.ModelSerializer):
    joined = serializers.CharField(source="created_at")
    roles = serializers.SerializerMethodField()
    dynamic_type = serializers.SerializerMethodField()
    interest_selected = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "muid",
            "full_name",
            "email",
            "mobile",
            "gender",
            "dob",
            "exist_in_guild",
            "joined",
            "roles",
            "profile_pic",
            "dynamic_type",
            "interest_selected",
        ]

    def get_interest_selected(self, obj):
        if not UserInterests.objects.filter(user=obj).exists():
            return "Please select your interests"
        return None

    def get_roles(self, obj):
        return [
            user_role_link.role.title
            for user_role_link in obj.user_role_link_user.all()
        ]

    def get_dynamic_type(self, obj):
        return {
            dynamic_role.type
            for dynamic_role in DynamicRole.objects.filter(
                role__title__in=self.get_roles(obj)
            )
        }.union(
            {dynamic_user.type for dynamic_user in DynamicUser.objects.filter(user=obj)}
        )


class CollegeSerializer(serializers.ModelSerializer):
    org_type = serializers.CharField(source="org.org_type")
    department = serializers.CharField(source="department.pk", allow_null=True)
    country = serializers.CharField(
        source="org.district.zone.state.country.pk", allow_null=True
    )
    state = serializers.CharField(source="org.district.zone.state.pk", allow_null=True)
    district = serializers.CharField(source="org.district.pk", allow_null=True)

    class Meta:
        model = UserOrganizationLink
        fields = [
            "org",
            "org_type",
            "department",
            "graduation_year",
            "country",
            "state",
            "district",
        ]


class OrgSerializer(serializers.ModelSerializer):
    org_type = serializers.CharField(source="org.org_type", read_only=True)

    class Meta:
        model = UserOrganizationLink
        fields = ["org", "org_type"]


class UserDetailsSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source="id")

    igs = serializers.ListField(write_only=True)
    department = serializers.CharField(write_only=True)
    graduation_year = serializers.CharField(write_only=True)

    organizations = serializers.SerializerMethodField(read_only=True)
    interest_groups = serializers.SerializerMethodField(read_only=True)
    role = serializers.SerializerMethodField(read_only=True)
    district = serializers.CharField(source="district.id", allow_null=True)

    class Meta:
        model = User
        fields = [
            "user_id",
            "full_name",
            "email",
            "mobile",
            "gender",
            "discord_id",
            "dob",
            "role",
            "organizations",
            "department",
            "graduation_year",
            "interest_groups",
            "igs",
            "district",
        ]

    def validate(self, data):
        if "id" not in data:
            raise serializers.ValidationError("User id is a required field")

        if (
            "email" in data
            and User.objects.filter(email=data["email"])
            .exclude(id=data["user_id"].id)
            .all()
        ):
            raise serializers.ValidationError("This email is already in use")
        return super().validate(data)

    def update(self, instance, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context["request"])
        admin = User.objects.get(id=user_id)
        user = User.objects.get(id=validated_data["id"])
        orgs = validated_data.get("orgs")
        department = validated_data.get("department")
        graduation_year = validated_data.get("graduation_year")
        interest_groups = validated_data.get("igs")

        with transaction.atomic():
            if orgs is not None:
                existing_orgs = UserOrganizationLink.objects.filter(user=user)
                new_orgs = [
                    UserOrganizationLink(
                        id=uuid.uuid4(),
                        user=user,
                        org_id=org_id,
                        created_by=admin,
                        created_at=DateTimeUtils.get_current_utc_time(),
                        verified=True,
                        department_id=department,
                        graduation_year=graduation_year,
                    )
                    for org_id in orgs
                ]
                existing_orgs.delete()
                UserOrganizationLink.objects.bulk_create(new_orgs)

            if interest_groups is not None:
                existing_ig = UserIgLink.objects.filter(user=user)
                new_ig = [
                    UserIgLink(
                        id=uuid.uuid4(),
                        user=user,
                        ig_id=ig,
                        created_by=admin,
                        created_at=DateTimeUtils.get_current_utc_time(),
                    )
                    for ig in interest_groups
                ]
                existing_ig.delete()
                UserIgLink.objects.bulk_create(new_ig)

            return super().update(instance, validated_data)

    def get_organizations(self, user):
        organization_links = user.user_organization_link_user.select_related("org")
        if not organization_links.exists():
            return None

        organizations_data = []
        for link in organization_links:
            if (
                link.org.org_type == OrganizationType.COLLEGE.value
                or OrganizationType.SCHOOL.value
            ):
                serializer = CollegeSerializer(link)
            else:
                serializer = OrgSerializer(link)

            organizations_data.append(serializer.data)
        return organizations_data

    def get_interest_groups(self, user):
        return user.user_ig_link_user.all().values_list("ig", flat=True)

    def get_role(self, user):
        return user.user_role_link_user.all().values_list("role", flat=True)


class UserVerificationSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField(source="user.full_name")
    user_id = serializers.ReadOnlyField(source="user.id")
    discord_id = serializers.ReadOnlyField(source="user.discord_id")
    muid = serializers.ReadOnlyField(source="user.muid")
    email = serializers.ReadOnlyField(source="user.email")
    mobile = serializers.ReadOnlyField(source="user.mobile")
    role_title = serializers.ReadOnlyField(source="role.title")

    class Meta:
        model = UserRoleLink
        fields = [
            "id",
            "user_id",
            "discord_id",
            "muid",
            "full_name",
            "verified",
            "role_id",
            "role_title",
            "email",
            "mobile",
        ]


class UserDetailsEditSerializer(serializers.ModelSerializer):
    organizations = serializers.ListField(write_only=True)
    roles = serializers.ListField(write_only=True)
    interest_groups = serializers.ListField(write_only=True)
    department = serializers.CharField(write_only=True)
    graduation_year = serializers.CharField(write_only=True)
    admin = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "email",
            "mobile",
            "gender",
            "dob",
            "organizations",
            "roles",
            "discord_id",
            "interest_groups",
            "department",
            "graduation_year",
            "admin",
            "district",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if (
            college := instance.user_organization_link_user.filter(
                org__org_type=OrganizationType.COLLEGE.value
            )
            .select_related("org__district__zone__state__country", "department")
            .first()
        ):
            data.update(
                {
                    "country": getattr(college.district.zone.state.country, "id", None),
                    "state": getattr(college.district.zone.state, "id", None),
                    "district": getattr(college.district, "id", None),
                    "department": getattr(college.department, "id", None),
                    "graduation_year": college.graduation_year,
                }
            )

        data.update(
            {
                "organizations": list(
                    instance.user_organization_link_user.all().values_list(
                        "org_id", flat=True
                    )
                ),
                "roles": list(
                    instance.user_role_link_user.all().values_list("role_id", flat=True)
                ),
                "interest_groups": list(
                    instance.user_ig_link_user.all().values_list("ig_id", flat=True)
                ),
            }
        )

        return data

    def update(self, instance, validated_data):
        admin = validated_data.pop("admin")
        admin = User.objects.filter(id=admin).first()
        current_time = DateTimeUtils.get_current_utc_time()

        with transaction.atomic():
            if isinstance(
                organization_ids := validated_data.pop("organizations", None), list
            ):
                instance.user_organization_link_user.all().delete()
                organizations = Organization.objects.filter(
                    id__in=organization_ids
                ).order_by("org_type")

                if (
                    organizations.exists()
                    and organizations.first().org_type != OrganizationType.COLLEGE.value
                ):
                    validated_data.pop("department", None)
                    validated_data.pop("graduation_year", None)

                UserOrganizationLink.objects.bulk_create(
                    [
                        UserOrganizationLink(
                            user=instance,
                            org=org,
                            created_by=admin,
                            created_at=current_time,
                            verified=True,
                            department_id=validated_data.pop("department", None),
                            graduation_year=validated_data.pop("graduation_year", None),
                        )
                        for org in organizations
                    ]
                )

            if isinstance(role_ids := validated_data.pop("roles", None), list):
                instance.user_role_link_user.all().delete()
                UserRoleLink.objects.bulk_create(
                    [
                        UserRoleLink(
                            user=instance,
                            role_id=role_id,
                            created_by=admin,
                            created_at=current_time,
                            verified=True,
                        )
                        for role_id in role_ids
                    ]
                )

            if isinstance(
                interest_group_ids := validated_data.pop("interest_groups", None), list
            ):
                instance.user_ig_link_user.all().delete()
                UserIgLink.objects.bulk_create(
                    [
                        UserIgLink(
                            user=instance,
                            ig_id=ig,
                            created_by=admin,
                            created_at=current_time,
                        )
                        for ig in interest_group_ids
                    ]
                )

            return super().update(instance, validated_data)


class UserOrgLinkSerializer(serializers.ModelSerializer):
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=False, allow_null=True
    )
    graduation_year = serializers.CharField(required=False, allow_null=True)
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(), many=False, required=True
    )
    is_alumni = serializers.BooleanField(required=False)

    def create(self, validated_data):
        department = validated_data.get("department", None)
        graduation_year = validated_data.get("graduation_year", None)
        is_alumni = validated_data.get("is_alumni", False)
        is_college = lambda org: org.org_type == OrganizationType.COLLEGE.value
        user_id = self.context.get("user")

        org_link = UserOrganizationLink.objects.create(
            user=user_id,
            org=validated_data.get("organization"),
            created_by=user_id,
            created_at=DateTimeUtils.get_current_utc_time(),
            verified=True,
            department=(
                department if is_college(validated_data.get("organization")) else None
            ),
            graduation_year=(
                graduation_year
                if is_college(validated_data.get("organization"))
                else None
            ),
            is_alumni=(
                is_alumni if is_college(validated_data.get("organization")) else None
            ),
        )
        if is_college(validated_data.get("organization")):
            student_role_id = (
                Role.objects.only("id").get(title=RoleType.STUDENT.value).id
            )
            if not UserRoleLink.objects.filter(
                user=user_id, role_id=student_role_id
            ).exists():
                UserRoleLink.objects.create(
                    user=user_id,
                    role_id=student_role_id,
                    created_by=user_id,
                    created_at=DateTimeUtils.get_current_utc_time(),
                    verified=True,
                )
        return org_link

    class Meta:
        model = UserOrganizationLink
        fields = ["organization", "department", "graduation_year", "is_alumni"]


class GetUserLinkSerializer(serializers.ModelSerializer):
    org_id = serializers.CharField(source="org.id")
    org_title = serializers.CharField(source="org.title")
    dept_id = serializers.CharField(
        source="department.id", allow_null=True, required=False
    )
    dept_title = serializers.CharField(
        source="department.title", allow_null=True, required=False
    )
    is_alumni = serializers.BooleanField()

    class Meta:
        model = UserOrganizationLink
        fields = ["org_id", "org_title", "dept_id", "dept_title", "is_alumni"]
