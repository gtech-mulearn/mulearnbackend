import uuid

from django.db import transaction
from rest_framework import serializers

from db.organization import UserOrganizationLink
from db.task import UserIgLink, Level, TotalKarma
from db.user import User, UserRoleLink
from utils.permission import JWTUtils
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils


class UserDashboardSerializer(serializers.Serializer):
    id = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    muid = serializers.CharField()
    discord_id = serializers.CharField()
    email = serializers.CharField()
    mobile = serializers.CharField()
    created_at = serializers.DateTimeField()
    karma = serializers.IntegerField()
    level = serializers.CharField()

    class Meta:
        fields = [
            "id",
            "first_name",
            "last_name",
            "muid",
            "discord_id"
            "email",
            "mobile",
            "created_at"
        ]


class UserSerializer(serializers.ModelSerializer):
    muid = serializers.CharField(source="mu_id")
    joined = serializers.CharField(source="created_at")
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "muid",
            "first_name",
            "last_name",
            "email",
            "mobile",
            "gender",
            "dob",
            "active",
            "exist_in_guild",
            "joined",
            "roles",
            "profile_pic",
        ]

    def get_roles(self, obj):
        return [
            user_role_link.role.title
            for user_role_link in obj.user_role_link_user.all()
        ]


class CollegeSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="org.title")
    org_type = serializers.CharField(source="org.org_type")
    department = serializers.CharField(source="department.title")

    class Meta:
        model = UserOrganizationLink
        fields = [
            "title",
            "org_type",
            "department",
            "graduation_year",
            "country",
            "state",
            "district",
        ]


class CommunitySerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="org.title", read_only=True)
    org_type = serializers.CharField(source="org.org_type", read_only=True)

    class Meta:
        model = UserOrganizationLink
        fields = ["title", "org_type"]


class CompanySerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="org.title", read_only=True)
    org_type = serializers.CharField(source="org.org_type", read_only=True)

    class Meta:
        model = UserOrganizationLink
        fields = ["title", "org_type"]


class UserEditSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source="id")
    organizations = serializers.SerializerMethodField(read_only=True)
    interest_groups = serializers.SerializerMethodField(read_only=True)
    igs = serializers.ListField(write_only=True)
    orgs = serializers.ListField(write_only=True)
    role = serializers.SerializerMethodField(read_only=True)
    department = serializers.CharField(write_only=True)
    graduation_year = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "user_id",
            "first_name",
            "last_name",
            "email",
            "mobile",
            "gender",
            "dob",
            "role",
            "organizations",
            "orgs",
            "department",
            "graduation_year",
            "interest_groups",
            "igs",
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
            if link.org.org_type == OrganizationType.COLLEGE.value:
                serializer = CollegeSerializer(link)
            elif link.org.org_type == OrganizationType.COMPANY.value:
                serializer = CompanySerializer(link)
            else:
                serializer = CommunitySerializer(link)

            organizations_data.append(serializer.data)
        return organizations_data

    def get_interest_groups(self, user):
        igs = user.user_ig_link_user.all()
        if igs:
            igs = [ig.ig.name for ig in igs]
        return igs

    def get_role(self, user):
        role = UserRoleLink.objects.filter(user=user).first()
        if role and role.role.title in [RoleType.STUDENT.value, RoleType.ENABLER.value]:
            return role.role.title
        return None


class UserVerificationSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField(source="user.fullname")
    user_id = serializers.ReadOnlyField(source="user.id")
    discord_id = serializers.ReadOnlyField(source="user.discord_id")
    mu_id = serializers.ReadOnlyField(source="user.mu_id")
    email = serializers.ReadOnlyField(source="user.email")
    role_title = serializers.ReadOnlyField(source="role.title")

    class Meta:
        model = UserRoleLink
        fields = [
            "id",
            "user_id",
            "discord_id",
            "mu_id",
            "full_name",
            "verified",
            "role_id",
            "role_title",
            "email",
        ]


class UserDetailsEditSerializer(serializers.ModelSerializer):
    organizations = serializers.ListField(write_only=True)
    roles = serializers.ListField(write_only=True)
    interest_groups = serializers.ListField(write_only=True)
    department = serializers.CharField(write_only=True)
    graduation_year = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "mobile",
            "gender",
            "dob",
            "organizations",
            "roles",
            "interest_groups",
            "department",
            "graduation_year",
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
        admin = self.context.get("admin")
        current_time = DateTimeUtils.get_current_utc_time()

        with transaction.atomic():
            if isinstance(
                    organization_ids := validated_data.pop("organizations", None), list
            ):
                instance.user_organization_link_user.all().delete()
                UserOrganizationLink.objects.bulk_create(
                    [
                        UserOrganizationLink(
                            user=instance,
                            org_id=org_id,
                            created_by=admin,
                            created_at=current_time,
                            verified=True,
                            department_id=validated_data.get("department", None),
                            graduation_year=validated_data.get("graduation_year", None),
                        )
                        for org_id in organization_ids
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



