from rest_framework import serializers

from db.user import User, UserRoleLink
from utils.types import OrganizationType
from db.organization import Organization, UserOrganizationLink


class UserDashboardSerializer(serializers.ModelSerializer):
    college = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    total_karma = serializers.SerializerMethodField()
    graduation_year = serializers.SerializerMethodField()

    def get_total_karma(self, obj):
        karma = obj.total_karma_user.karma if hasattr(obj, "total_karma_user") else 0
        return karma

    def get_company(self, obj):
        user_id = obj.id
        if (
            organization_id := UserOrganizationLink.objects.filter(
                user_id=user_id, verified=True
            )
            .values_list("org_id", flat=True)
            .first()
        ):
            company_title = (
                Organization.objects.filter(
                    id=organization_id, org_type=OrganizationType.COMPANY.value
                )
                .values_list("title", flat=True)
                .first()
            )
            return company_title or None

        return None

    def get_department(self, obj):
        link = UserOrganizationLink.objects.filter(user=obj, verified=True).first()
        return link.department.title if link and link.department else ""

    def get_graduation_year(self, obj):
        link = UserOrganizationLink.objects.filter(user=obj, verified=True).first()
        return link.graduation_year if link else ""

    def get_college(self, obj):
        user_id = obj.id
        if (
            organization_id := UserOrganizationLink.objects.filter(
                user_id=user_id, verified=True
            )
            .values_list("org_id", flat=True)
            .first()
        ):
            college_title = (
                Organization.objects.filter(
                    id=organization_id, org_type=OrganizationType.COLLEGE.value
                )
                .values_list("title", flat=True)
                .first()
            )
            return college_title or None

        return None

    class Meta:
        model = User
        fields = [
            "id",
            "discord_id",
            "first_name",
            "last_name",
            "email",
            "mobile",
            "gender",
            "dob",
            "admin",
            "active",
            "exist_in_guild",
            "created_at",
            "college",
            "company",
            "total_karma",
            "department",
            "graduation_year",
        ]
        read_only_fields = ["id", "created_at", "total_karma"]


class UserSerializer(serializers.ModelSerializer):
    muid = serializers.CharField(source="mu_id")
    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")
    existInGuild = serializers.BooleanField(source="exist_in_guild")
    joined = serializers.CharField(source="created_at")
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "muid",
            "firstName",
            "lastName",
            "email",
            "mobile",
            "gender",
            "dob",
            "active",
            "existInGuild",
            "joined",
            "roles",
        ]

    def get_roles(self, obj):
        return [
            user_role_link.role.title
            for user_role_link in obj.user_role_link_user.all()
        ]


class UserVerificationSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField(source="user.fullname")
    user_id = serializers.ReadOnlyField(source="user.id")
    discord_id = serializers.ReadOnlyField(source="user.discord_id")
    mu_id = serializers.ReadOnlyField(source="user.mu_id")
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
        ]
