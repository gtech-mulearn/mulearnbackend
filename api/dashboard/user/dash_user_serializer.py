import re
import uuid

from decouple import config as decouple_config
from django.db import transaction
from rest_framework import serializers

from db.company import Company
from db.organization import Department, Organization, UserOrganizationLink
from db.task import UserIgLink
from db.user import Role, User, UserDomains, UserMentor, UserRoleLink
from utils.permission import JWTUtils
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils, check_alumni_status
from db.user import DynamicRole, DynamicUser

# from db.user import UserInterests

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
    user_domains = serializers.SerializerMethodField()
    user_endgoals = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()

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
            "user_domains",
            "user_endgoals",
            "interested_in_work",
            "interested_in_gig_work",
            "company",
        ]

    # def get_interest_selected(self, obj):
    #     if not UserInterests.objects.filter(user=obj).exists():
    #         return "Please select your interests"
    #     return None
    def get_user_domains(self, obj):
        return obj.user_domains.values_list("domain_name", flat=True)

    def get_user_endgoals(self, obj):
        return obj.user_endgoals.values_list("endgoal_name", flat=True)

    def get_roles(self, obj):
        return [
            user_role_link.role.title
            for user_role_link in obj.user_role_link_user.all()
        ]

    def get_dynamic_type(self, obj):
        dynamic_types = {
            dynamic_role.type
            for dynamic_role in DynamicRole.objects.filter(
                role__title__in=self.get_roles(obj)
            )
        }.union(
            {dynamic_user.type for dynamic_user in DynamicUser.objects.filter(user=obj)}
        )

        return sorted(dynamic_type for dynamic_type in dynamic_types if dynamic_type is not None)

    def get_company(self, obj):
        roles = self.get_roles(obj)
        if RoleType.COMPANY.value in roles:
            company_link = obj.user_organization_link_user.filter(
                org__org_type=OrganizationType.COMPANY.value
            ).first()
            if company_link:
                return company_link.org.title
        return None


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
                        is_alumni=check_alumni_status(graduation_year),
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
        organization_links = user.user_organization_link_user.select_related(
            "org__district__zone__state__country", "department"
        )
        if not organization_links.exists():
            return None

        organizations_data = []
        for link in organization_links:
            if link.org.org_type in (OrganizationType.COLLEGE.value, OrganizationType.SCHOOL.value):
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
    # Core user identity
    user_id = serializers.ReadOnlyField(source="user.id")
    full_name = serializers.ReadOnlyField(source="user.full_name")
    muid = serializers.ReadOnlyField(source="user.muid")
    discord_id = serializers.ReadOnlyField(source="user.discord_id")
    email = serializers.ReadOnlyField(source="user.email")
    mobile = serializers.ReadOnlyField(source="user.mobile")
    gender = serializers.ReadOnlyField(source="user.gender")
    dob = serializers.ReadOnlyField(source="user.dob")
    joined = serializers.ReadOnlyField(source="user.created_at")


    # Geographic info
    district = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()

    # Role info
    role_title = serializers.ReadOnlyField(source="role.title")

    # Related data
    organizations = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()

    # Role-specific profile
    role_profile = serializers.SerializerMethodField()

    class Meta:
        model = UserRoleLink
        fields = [
            "id",
            "user_id",
            "full_name",
            "muid",
            "discord_id",
            "email",
            "mobile",
            "gender",
            "dob",
            "joined",
            "district",
            "state",
            "country",
            "verified",
            "role_id",
            "role_title",
            "organizations",
            "interest_groups",
            "role_profile",
        ]

    def get_district(self, obj):
        district = obj.user.district
        if district:
            return {"id": district.id, "name": district.name}
        return None

    def get_state(self, obj):
        try:
            state = obj.user.district.zone.state
            return {"id": state.id, "name": state.name}
        except AttributeError:
            return None

    def get_country(self, obj):
        try:
            country = obj.user.district.zone.state.country
            return {"id": country.id, "name": country.name}
        except AttributeError:
            return None

    def get_organizations(self, obj):
        # Use .all() so Django resolves results from _prefetched_objects_cache.
        # Calling .select_related() here would clone the queryset and clear the
        # cache, issuing a new SQL query per user (N+1).
        result = []
        for link in obj.user.user_organization_link_user.all():
            result.append({
                "org_id": link.org.id if link.org else None,
                "org_title": link.org.title if link.org else None,
                "org_type": link.org.org_type if link.org else None,
                "department": link.department.title if link.department else None,
                "graduation_year": link.graduation_year,
                "verified": link.verified,
            })
        return result

    def get_interest_groups(self, obj):
        # Use .all() to stay in _prefetched_objects_cache; .select_related()
        # or .values_list() would clone the queryset and bypass the prefetch cache.
        return [
            link.ig.name
            for link in obj.user.user_ig_link_user.all()
            if link.ig
        ]

    def get_role_profile(self, obj):
        role_title = obj.role.title if obj.role else ""

        # ----- Mentor (all tiers) -----
        if RoleType.MENTOR.value in role_title or "Mentor" in role_title:
            # UserMentor is now a OneToOneField — the reverse accessor is a
            # single object (or raises DoesNotExist), not a related manager.
            try:
                mentor = obj.user.mentor_profile
            except Exception:
                mentor = None
            if mentor:
                from api.dashboard.mentor.dash_mentor_helper import get_mentor_scopes
                from db.user import MentorApplication

                scopes = get_mentor_scopes(obj.user_id)
                # "reason" lives on MentorApplication, not UserMentor — pull it
                # from the user's most recent application.
                latest_application = MentorApplication.objects.filter(
                    user_id=obj.user_id
                ).order_by('-created_at').first()
                return {
                    "type": "mentor",
                    "tiers": sorted({scope_type for scope_type, _ in scopes}),
                    "about": mentor.about,
                    "expertise": mentor.expertise,
                    "reason": latest_application.reason if latest_application else None,
                    "hours_available": mentor.hours,
                    "is_active": mentor.is_active,
                }
            return {"type": "mentor"}

        # ----- Company -----
        if RoleType.COMPANY.value in role_title or "Company" in role_title:
            company = getattr(obj.user, "company_profile", None)
            if company:
                return {
                    "type": "company",
                    "company_id": company.id,
                    "name": company.name,
                    "slug": company.slug,
                    "description": company.description,
                    "industry_sector": company.industry_sector,
                    "company_size": company.company_size,
                    "website_link": company.website_link,
                    "linkedin_url": company.linkedin_url,
                    "location": company.location,
                    "legal_name": company.legal_name,
                    "registration_number": company.registration_number,
                    "tax_id": company.tax_id,
                    "status": company.status,
                    "verification_document_url": company.verification_document_url,
                    "verification_requested_at": company.verification_requested_at,
                    "rejection_reason": company.rejection_reason,
                    "founded_year": company.founded_year,
                }
            return {"type": "company"}

        # ----- Enabler -----
        if RoleType.ENABLER.value in role_title or "Enabler" in role_title:
            # Enablers do not have a dedicated profile table.
            # Their key info is surfaced through the expanded user fields above.
            return {
                "type": "enabler",
                "note": "Enabler-specific details are covered by the user fields above.",
            }

        # ----- Other / Unknown role -----
        return None


class UserDetailsEditSerializer(serializers.ModelSerializer):
    organizations = serializers.ListField(write_only=True)
    roles = serializers.ListField(write_only=True)
    interest_groups = serializers.ListField(write_only=True)
    department = serializers.CharField(write_only=True)
    graduation_year = serializers.CharField(write_only=True, required=False, allow_null=True)
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

    def validate_interest_groups(self, interest_group_ids):
        if len(interest_group_ids) > 3:
            raise serializers.ValidationError(
                "Cannot select more than 3 interest groups"
            )
        return interest_group_ids

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if (
            college := instance.user_organization_link_user.filter(
                org__org_type=OrganizationType.COLLEGE.value
            )
            .order_by("-created_at", "-id")
            .select_related("org__district__zone__state__country", "department")
            .first()
        ):
            data.update(
                {
                    "country": getattr(college.org.district.zone.state.country, "id", None) if college.org.district else None,
                    "state": getattr(college.org.district.zone.state, "id", None) if college.org.district else None,
                    "district": getattr(college.org.district, "id", None) if college.org.district else None,
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

                # Extract these before the loop so all orgs get the correct value
                department_id = validated_data.pop("department", None)
                graduation_year = validated_data.pop("graduation_year", None)

                if (
                    organizations.exists()
                    and organizations.first().org_type != OrganizationType.COLLEGE.value
                ):
                    department_id = None
                    graduation_year = None

                UserOrganizationLink.objects.bulk_create(
                    [
                        UserOrganizationLink(
                            user=instance,
                            org=org,
                            created_by=admin,
                            created_at=current_time,
                            verified=True,
                            department_id=department_id,
                            graduation_year=graduation_year,
                            is_alumni=check_alumni_status(graduation_year),
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


class UserOrgLinkSerializer(serializers.Serializer):
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=False, allow_null=True
    )
    graduation_year = serializers.CharField(required=False, allow_null=True)
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(), many=False, required=True, allow_null=True
    )
    is_alumni = serializers.BooleanField(required=False)
    is_student = serializers.BooleanField(
        required=False, allow_null=True, default=False
    )

    def create(self, validated_data):
        department = validated_data.get("department", None)
        graduation_year = validated_data.get("graduation_year", None)
        # Always compute is_alumni from graduation_year; ignore any client-supplied value.
        is_alumni = check_alumni_status(graduation_year)
        is_college = lambda org: org.org_type == OrganizationType.COLLEGE.value
        user_id = self.context.get("user")
        with transaction.atomic():
            org = validated_data.get("organization")
            if org is None:
                return "skiped_creation"

            college_link = is_college(org)
            if college_link:
                existing_links = list(
                    UserOrganizationLink.objects.filter(
                        user=user_id,
                        org__org_type=OrganizationType.COLLEGE.value,
                    ).order_by("-created_at", "-id")
                )

                if existing_links:
                    org_link = existing_links[0]
                    org_link.org = org
                    org_link.department = department
                    org_link.graduation_year = graduation_year
                    org_link.is_alumni = is_alumni
                    org_link.verified = True
                    org_link.created_by = user_id
                    org_link.save(
                        update_fields=[
                            "org",
                            "department",
                            "graduation_year",
                            "is_alumni",
                            "verified",
                            "created_by",
                        ]
                    )

                    if len(existing_links) > 1:
                        UserOrganizationLink.objects.filter(
                            id__in=[link.id for link in existing_links[1:]]
                        ).delete()
                else:
                    org_link = UserOrganizationLink.objects.create(
                        user=user_id,
                        org=org,
                        created_by=user_id,
                        created_at=DateTimeUtils.get_current_utc_time(),
                        verified=True,
                        department=department,
                        graduation_year=graduation_year,
                        is_alumni=is_alumni,
                    )
            else:
                org_link = UserOrganizationLink.objects.create(
                    user=user_id,
                    org=org,
                    created_by=user_id,
                    created_at=DateTimeUtils.get_current_utc_time(),
                    verified=True,
                    department=None,
                    graduation_year=None,
                    is_alumni=None,
                )

            if validated_data.get("is_student") or (
                validated_data.get("organization")
                and is_college(validated_data.get("organization"))
            ):
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
        fields = [
            "organization",
            "department",
            "graduation_year",
            "is_alumni",
            "is_student",
        ]


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


class UserBasicDetailsSerializer(serializers.ModelSerializer):
    interest_groups = serializers.SerializerMethodField()
    organizations = serializers.SerializerMethodField()
    karma = serializers.CharField(source="wallet_user.karma")

    class Meta:
        model = User
        fields = (
            "id",
            "full_name",
            "muid",
            "interest_groups",
            "organizations",
            "profile_pic",
            "karma",
        )

    def get_organizations(self, obj):
        # Use .all() so Django resolves results from _prefetched_objects_cache (the
        # view's Prefetch already carries select_related("org").only(...)). Chaining
        # .select_related()/.only() here would clone the queryset and bypass the
        # cache, issuing a new SQL query per user (N+1).
        org_links = obj.user_organization_link_user.all()
        data = []
        for org_link in org_links:
            data.append(
                {
                    "id": org_link.org.id,
                    "title": org_link.org.title,
                    "code": org_link.org.code,
                    "org_type": org_link.org.org_type,
                }
            )
        return data

    def get_interest_groups(self, obj):
        # Same _prefetched_objects_cache reasoning as get_organizations above.
        ig_links = obj.user_ig_link_user.all()
        data = []
        for ig_link in ig_links:
            data.append({"id": ig_link.ig.id, "name": ig_link.ig.name})
        return data
