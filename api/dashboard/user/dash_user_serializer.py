from os import write
from rest_framework import serializers

from db.organization import Organization, UserOrganizationLink
from db.user import User, UserRoleLink
from utils.permission import JWTUtils
from utils.types import OrganizationType, RoleType


class UserDashboardSerializer(serializers.ModelSerializer):
    total_karma = serializers.IntegerField()
    company = serializers.CharField()
    college = serializers.CharField()
    department = serializers.CharField()
    graduation_year = serializers.CharField()

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
            "company",
            "college",
            "total_karma",
            "department",
            "graduation_year",
        ]
        read_only_fields = ["id", "created_at", "total_karma"]


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
    link_id = serializers.CharField(source="id")
    org_id = serializers.CharField(write_only=True)
    department_id = serializers.CharField(source="department", write_only=True)
    title = serializers.CharField(source="org.title")
    org_type = serializers.CharField(source="org.org_type")
    department = serializers.CharField(source="department.title")

    def update(self, instance, validated_data):
        validated_data["department"] = validated_data.pop("department_id")
        return super().update(instance, validated_data)

    class Meta:
        model = UserOrganizationLink
        fields = [
            "link_id",
            "org_id",
            "title",
            "org_type",
            "department",
            "department_id",
            "graduation_year",
            "country",
            "state",
            "district",
        ]
        read_only_fields = [
            "department",
            "title",
            "org_type",
            "country",
            "state",
            "district",
        ]


class CommunitySerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(write_only=True)
    org_id = serializers.CharField(write_only=True)
    title = serializers.CharField(source="org.title", read_only=True)
    org_type = serializers.CharField(source="org.org_type", read_only=True)

    def create(self, instance, validated_data):
        user_links = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COMMUNITY.value,
            user=self.context["user_id"],
        )
        user_links.delete()

        return super().create(instance, validated_data)

    class Meta:
        model = UserOrganizationLink
        fields = ["title", "org_type", "org_id", "user_id"]


class CompanySerializer(serializers.ModelSerializer):
    link_id = serializers.CharField(source="id")
    org_id = serializers.CharField(write_only=True)
    title = serializers.CharField(source="org.title", read_only=True)
    org_type = serializers.CharField(source="org.org_type", read_only=True)

    class Meta:
        model = UserOrganizationLink
        fields = ["link_id", "title", "org_type", "org_id"]


class UserEditSerializer(serializers.ModelSerializer):
    organizations = serializers.SerializerMethodField(read_only=True)
    role = serializers.SerializerMethodField(read_only=True)
    community = serializers.ListField(write_only=True)
    college = serializers.DictField(write_only=True)
    company = serializers.DictField(write_only=True)

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
            "role",
            "community",
            "college",
            "company",
        ]
        read_only_fields = [
            "email",
        ]

    def validate(self, data):
        user_id = "51175869-241f-49c9-a028-5d0e4b869589"
        # user_id = JWTUtils.fetch_user_id(self.context["request"])
        # admin = User.objects.get(id=user_id)
        data["created_by"] = user_id
        data["verified"] = True

        if "company" in data:
            data["company"]["user_id"] = data["id"]
            company_serializer = CompanySerializer(data=data["company"], context=data["id"])
            if not company_serializer.is_valid():
                raise serializers.ValidationError(company_serializer.errors)
            data["company"] = company_serializer

        if "college" in data:
            data["college"]["user_id"] = data["id"]
            college_serializer = CollegeSerializer(data=data["college"], context=data["id"])
            if not college_serializer.is_valid():
                raise serializers.ValidationError(college_serializer.errors)
            data["college"] = college_serializer

        if "community" in data:
            data["community"]["user_id"] = data["id"]
            community_serializer = CommunitySerializer(data=data["community"], context=data["id"])
            if not community_serializer.is_valid():
                raise serializers.ValidationError(community_serializer.errors)
            data["community"] = community_serializer

        return super().validate(data)

    def update(self, instance, validated_data):
        user_id = "51175869-241f-49c9-a028-5d0e4b869589"
        # user_id = JWTUtils.fetch_user_id(self.context["request"])
        admin = User.objects.get(id=user_id)
        validated_data["created_by"] = admin
        validated_data["verified"] = True

        if "company" in validated_data:
            validated_data["company"].save()

        if "college" in validated_data:
            college_serializer = CollegeSerializer(
                data=validated_data.pop("college"), context=validated_data["id"]
            )
            college_serializer.save()

        if "community" in validated_data:
            community_serializer = CommunitySerializer(
                data=validated_data.pop("community"), context=validated_data["id"]
            )
            community_serializer.save()

        return super().update(instance, validated_data)

    def get_organizations(self, user):
        organization_links = user.user_organization_link_user_id.select_related("org")
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
