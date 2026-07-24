import uuid
from datetime import timedelta

from django.db.models import Sum
from django.db import transaction
from rest_framework import serializers

from db.organization import Organization, UserOrganizationLink, College, CollegeShowcase
from db.task import KarmaActivityLog, InterestGroup, UserIgLink
from db.campus import CampusIGChapter, CampusSocialLink
from db.user import User, UserRoleLink
from utils.types import OrganizationType
from utils.types import RoleType, SocialPlatformType
from utils.utils import DateTimeUtils
from .dash_campus_helper import validate_campus_member, assign_ig_campus_lead
from db.events import Event
from db.learning_circle import LearningCircle, UserCircleLink

class CampusDetailsPublicSerializer(serializers.ModelSerializer):
    org_id = serializers.ReadOnlyField(source="id")
    college_name = serializers.ReadOnlyField(source="title")
    campus_code = serializers.ReadOnlyField(source="code")
    campus_zone = serializers.ReadOnlyField(source="district.zone.name")
    campus_level = serializers.SerializerMethodField()
    total_karma = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    social_links = serializers.SerializerMethodField()
   
    

    class Meta:
        model = Organization
        fields = [
            "org_id",
            "college_name",
            "campus_code",
            "campus_zone",
            "campus_level",
            "total_karma",
            "total_members",
            "active_members",
            "rank",
            "social_links",
        ]

    def get_campus_level(self, obj):
        campus = obj.college_org
        if campus:
            return campus.level

        return None

    def get_total_members(self, obj):
        return obj.user_organization_link_org.filter(verified=True).values('user').distinct().count()

    def get_active_members(self, obj):
        return obj.user_organization_link_org.filter(
            verified=True,
            user__discord_id__isnull=False,
            user__exist_in_guild=True
        ).values('user').distinct().count()

    def get_total_karma(self, obj):
        from db.task import Wallet
        users_in_org = obj.user_organization_link_org.filter(verified=True).values_list('user', flat=True)
        return Wallet.objects.filter(
            user__in=users_in_org
        ).aggregate(total_karma=Sum("karma"))["total_karma"] or 0

    def get_rank(self, obj):
        # (org, user, karma) collapsed via .distinct() so a user with more than
        # one org-link row to the same college can't inflate that college's
        # karma total relative to every other college in this ranking.
        rows = (
            UserOrganizationLink.objects.filter(
                org__org_type=OrganizationType.COLLEGE.value,
                verified=True,
            )
            .values("org", "user", "user__wallet_user__karma")
            .distinct()
            .order_by("org__created_at")
        )

        rank_dict = {}
        for row in rows:
            org_id = row["org"]
            rank_dict[org_id] = rank_dict.get(org_id, 0) + (row["user__wallet_user__karma"] or 0)

        sorted_rank_dict = dict(
            sorted(rank_dict.items(), key=lambda x: x[1], reverse=True)
        )

        if obj.id in sorted_rank_dict:
            keys_list = list(sorted_rank_dict.keys())
            position = keys_list.index(obj.id)
            return position + 1

    def get_social_links(self, obj):
        links = CampusSocialLink.objects.filter(org=obj)
        return CampusSocialLinkSerializer(links, many=True).data



class CampusListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "title", "code"]


class CampusDetailsSerializer(serializers.ModelSerializer):
    org_id = serializers.ReadOnlyField(source="org.id")
    college_name = serializers.ReadOnlyField(source="org.title")
    campus_code = serializers.ReadOnlyField(source="org.code")
    campus_zone = serializers.ReadOnlyField(source="org.district.zone.name")
    campus_level = serializers.SerializerMethodField()
    total_karma = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()

    lead = serializers.SerializerMethodField()
    karma_last_7_days = serializers.SerializerMethodField()
    karma_last_30_days = serializers.SerializerMethodField()
    active_ig_count = serializers.SerializerMethodField()
    social_links = serializers.SerializerMethodField()

    class Meta:
        model = UserOrganizationLink
        fields = [
            "org_id",
            "college_name",
            "campus_code",
            "campus_zone",
            "campus_level",
            "total_karma",
            "total_members",
            "active_members",
            "rank",
            "lead",
            "karma_last_7_days",
            "karma_last_30_days",
            "active_ig_count",
            "social_links",
        ]

    def get_lead(self, obj):

        campus_lead = User.objects.filter(
            user_organization_link_user__org=obj.org,
            user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            user_organization_link_user__verified=True,
            user_role_link_user__role__title=RoleType.CAMPUS_LEAD.value,
        ).first()
        if campus_lead:
            campus_lead = campus_lead.full_name

        enabler = User.objects.filter(
            user_organization_link_user__org=obj.org,
            user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            user_organization_link_user__verified=True,
            user_role_link_user__role__title=RoleType.LEAD_ENABLER.value,
        ).first()
        if enabler:
            enabler = enabler.full_name

        return {"campus_lead": campus_lead, "enabler": enabler}

    def get_campus_level(self, obj):
        campus = College.objects.filter(org=obj.org).first()
        if campus:
            return campus.level

        return None

   

    def get_total_members(self, obj):
        return obj.org.user_organization_link_org.filter(verified=True).values('user').distinct().count()

    def get_active_members(self, obj):
        from db.task import Wallet

        last_month = DateTimeUtils.get_current_utc_time() - timedelta(
            weeks=26
        )  # 6months
        member_user_ids = obj.org.user_organization_link_org.filter(verified=True).values_list("user_id", flat=True).distinct()
        return Wallet.objects.filter(
            user_id__in=member_user_ids,
            karma_last_updated_at__gte=last_month,
        ).count()

    def get_total_karma(self, obj):
        from db.task import Wallet

        member_user_ids = obj.org.user_organization_link_org.filter(
            org__org_type=OrganizationType.COLLEGE.value,
            verified=True,
        ).values_list("user_id", flat=True).distinct()
        return Wallet.objects.filter(
            user_id__in=member_user_ids
        ).aggregate(total_karma=Sum("karma"))["total_karma"] or 0

    def get_rank(self, obj):
        # (org, user, karma) collapsed via .distinct() so a user with more than
        # one org-link row to the same college can't inflate that college's
        # karma total relative to every other college in this ranking.
        rows = (
            UserOrganizationLink.objects.filter(
                org__org_type=OrganizationType.COLLEGE.value,
                verified=True,
            )
            .values("org", "user", "user__wallet_user__karma")
            .distinct()
            .order_by("org__created_at")
        )

        rank_dict = {}
        for row in rows:
            org_id = row["org"]
            rank_dict[org_id] = rank_dict.get(org_id, 0) + (row["user__wallet_user__karma"] or 0)

        sorted_rank_dict = dict(
            sorted(rank_dict.items(), key=lambda x: x[1], reverse=True)
        )

        if obj.org.id in sorted_rank_dict:
            keys_list = list(sorted_rank_dict.keys())
            position = keys_list.index(obj.org.id)
            return position + 1
    def get_karma_last_7_days(self, obj):
        seven_days_ago = DateTimeUtils.get_current_utc_time() - timedelta(days=7)
        member_user_ids = obj.org.user_organization_link_org.filter(verified=True).values_list("user_id", flat=True).distinct()
        return (
            KarmaActivityLog.objects.filter(
                user_id__in=member_user_ids,
                created_at__gte=seven_days_ago,
                appraiser_approved=True,
            ).aggregate(total_karma=Sum("karma"))["total_karma"] or 0
        )

    def get_karma_last_30_days(self, obj):
        thirty_days_ago = DateTimeUtils.get_current_utc_time() - timedelta(days=30)
        member_user_ids = obj.org.user_organization_link_org.filter(verified=True).values_list("user_id", flat=True).distinct()
        return (
            KarmaActivityLog.objects.filter(
                user_id__in=member_user_ids,
                created_at__gte=thirty_days_ago,
                appraiser_approved=True,
            ).aggregate(total_karma=Sum("karma"))["total_karma"] or 0
        )
    def get_active_ig_count(self, obj):
        return CampusIGChapter.objects.filter(
            org=obj.org,
            is_active=True,
        ).count()

    def get_social_links(self, obj):
        links = CampusSocialLink.objects.filter(org=obj.org)
        return CampusSocialLinkSerializer(links, many=True).data


class CampusStudentDetailsSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    full_name = serializers.SerializerMethodField()
    muid = serializers.CharField()
    karma = serializers.IntegerField()
    rank = serializers.SerializerMethodField()
    level = serializers.CharField()
    # is_active = serializers.CharField()
    join_date = serializers.CharField()
    last_karma_gained = serializers.CharField()
    email = serializers.CharField()
    mobile = serializers.CharField()
    graduation_year = serializers.CharField()
    department = serializers.CharField()
    is_alumni = serializers.BooleanField()
    ig_count = serializers.IntegerField(default=0)
    lc_count = serializers.IntegerField(default=0)

    class Meta:
        fields = (
            "user_id",
            "email",
            "mobile",
            "full_name",
            "karma",
            "muid",
            "rank",
            "level",
            "join_date",
            "is_alumni",
            "last_karma_update_at",
            "ig_count",
            "lc_count"
        )

    def get_rank(self, obj):
        ranks = self.context.get("ranks")
        if ranks:
            return ranks.get(obj.id, None)
        return getattr(obj, "rank", None)

    def get_full_name(self, obj):
        return obj.full_name


class WeeklyKarmaSerializer(serializers.ModelSerializer):
    college_name = serializers.ReadOnlyField(source="title")

    class Meta:
        model = Organization
        fields = ["college_name"]

    def to_representation(self, instance):
        response = super().to_representation(instance)

        today = DateTimeUtils.get_current_utc_time().date()
        date_range = [today - timedelta(days=i) for i in range(7)]

        member_user_ids = instance.user_organization_link_org.filter(verified=True).values_list("user_id", flat=True).distinct()

        for date in date_range:
            karma_logs = KarmaActivityLog.objects.filter(
                user_id__in=member_user_ids,
                created_at__date=date,
                appraiser_approved=True,
            ).aggregate(
                karma=Sum("karma"),
            )
            response[str(date)] = karma_logs["karma"] or 0

        return response


class ChangeStudentTypeSerializer(serializers.Serializer):
    is_alumni = serializers.BooleanField(default=False)

    class Meta:
        model = UserOrganizationLink
        fields = ("is_alumni",)

    def update(self, instance, validated_data):
        instance.is_alumni = validated_data.get("is_alumni")
        instance.save()

        return instance


class ListAluminiSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    full_name = serializers.SerializerMethodField()
    muid = serializers.CharField()
    karma = serializers.IntegerField()
    rank = serializers.SerializerMethodField()
    level = serializers.CharField()
    join_date = serializers.CharField()

    class Meta:
        fields = ("user_id", "full_name", "karma", "muid", "rank", "level", "join_date")


class UserRoleLinkSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserRoleLink
        fields = [
            "user",
            "role",
        ]

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        validated_data["created_by_id"] = user_id
        validated_data["id"] = uuid.uuid4()
        validated_data["verified"] = True

        user_role_link = UserRoleLink.objects.create(**validated_data)
        return user_role_link


class CampusEventListSerializer(serializers.ModelSerializer):
    tags = serializers.JSONField()

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "status",
            "scope",
            "organiser_type",
            "start_datetime",
            "end_datetime",
            "venue_type",
            "venue_city",
            "interest_count",
            "cover_image",
            "tags",
        ]


class ExecomMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source="user.id")
    full_name = serializers.CharField(source="user.full_name")
    muid = serializers.CharField(source="user.muid")
    profile_pic = serializers.SerializerMethodField()
    role_title = serializers.CharField(source="role.title")
    ig_name = serializers.SerializerMethodField()

    class Meta:
        model = UserRoleLink
        fields = [
            "id",
            "user_id",
            "full_name",
            "muid",
            "profile_pic",
            "role_title",
            "ig_name",
        ]

    def get_profile_pic(self, obj):
        return str(obj.user.profile_pic) if obj.user.profile_pic else None

    def get_ig_name(self, obj):
        title = obj.role.title
        # IG campus lead roles use canonical format: "{ig_code} CampusLead"
        if title not in (
            RoleType.CAMPUS_LEAD.value,
            RoleType.LEAD_ENABLER.value,
        ) and title.endswith("CampusLead"):
            ig_name = title.replace("CampusLead", "").strip()
            return ig_name or None
        return None

        
class CampusLeaderboardSerializer(CampusStudentDetailsSerializer):
    # ── override fields (email & mobile removed — public endpoint) ──────────
    email           = None
    mobile          = None

    # ── NEW fields not in CampusStudentDetailsSerializer ────────────────────
    profile_pic     = serializers.SerializerMethodField()
    ig_count        = serializers.IntegerField(default=0)

    class Meta(CampusStudentDetailsSerializer.Meta):
        # inherit parent Meta and extend fields
        fields = (
            "rank",
            "user_id",
            "full_name",
            "muid",
            "profile_pic",       
            "karma",
            "level",
            "join_date",
            "last_karma_gained",
            "graduation_year",
            "department",
            "is_alumni",
            "ig_count",          
          
        )

    def get_profile_pic(self, obj):
        return str(obj.profile_pic) if obj.profile_pic else None
    # get_rank and get_full_name are inherited from CampusStudentDetailsSerializer


class CampusStudentListSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    muid = serializers.CharField()
    profile_pic = serializers.SerializerMethodField()

    class Meta:
        fields = ("full_name", "muid", "profile_pic")

    def get_profile_pic(self, obj):
        return str(obj.profile_pic) if getattr(obj, 'profile_pic', None) else None



class CampusIGChapterListSerializer(serializers.ModelSerializer):
    ig_id = serializers.ReadOnlyField(source="ig.id")
    ig_name = serializers.ReadOnlyField(source="ig.name")
    ig_code = serializers.ReadOnlyField(source="ig.code")
    ig_icon = serializers.ReadOnlyField(source="ig.icon")
    ig_cover_image = serializers.ReadOnlyField(source="ig.cover_image")
    ig_icon_image = serializers.ReadOnlyField(source="ig.icon_image")
    lead_id = serializers.ReadOnlyField(source="lead.id")
    lead_name = serializers.SerializerMethodField()
    campus_ig_member_count = serializers.SerializerMethodField()

    class Meta:
        model = CampusIGChapter
        fields = [
            "id",
            "ig_id",
            "ig_name",
            "ig_code",
            "ig_icon",
            "ig_cover_image",
            "ig_icon_image",
            "lead_id",
            "lead_name",
            "description",
            "icon_link",
            "is_active",
            "campus_ig_member_count",
        ]

    def get_lead_name(self, obj):
        if obj.lead:
            return obj.lead.full_name
        return None

    def get_campus_ig_member_count(self, obj):
        return UserIgLink.objects.filter(
            ig=obj.ig,
            is_active=True,
            assignment_type=UserIgLink.AssignmentType.LEARNER,
            user__user_organization_link_user__org=obj.org,
            user__user_organization_link_user__verified=True,
        ).values('user').distinct().count()


class CampusIGChapterCreateSerializer(serializers.ModelSerializer):
    # Accept muid instead of UUID pk so the frontend can pass e.g. "john-doe@mulearn"
    lead = serializers.SlugRelatedField(
        slug_field="muid",
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = CampusIGChapter
        fields = ["ig", "description", "icon_link", "lead"]

    def validate_ig(self, value):
        org = self.context.get("org")
        if CampusIGChapter.objects.filter(org=org, ig=value, is_active=True).exists():
            raise serializers.ValidationError("An active IG chapter already exists for this campus and IG.")
        return value

    def validate_lead(self, value):
        if value is None:
            return value
        org = self.context.get("org")
        if not validate_campus_member(value.id, org.id):
            raise serializers.ValidationError("The lead must be a member of this campus.")
        return value

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        org = self.context.get("org")
        validated_data["id"] = str(uuid.uuid4())
        validated_data["org"] = org
        validated_data["created_by_id"] = user_id
        validated_data["updated_by_id"] = user_id

        with transaction.atomic():
            chapter = CampusIGChapter.objects.create(**validated_data)

            if chapter.lead:
                # assign_ig_campus_lead handles bootstrapping the roles internally
                assign_ig_campus_lead(chapter, chapter.lead, user_id)
            else:
                # Ensure IG roles exist in the database
                ig_name = chapter.ig.name
                ig_code = chapter.ig.code

                roles_to_ensure = [
                    {
                        "title": ig_name,
                        "description": f"{ig_name} Interest Group Member",
                    },
                    {
                        "title": RoleType.IG_CAMPUS_LEAD_ROLE(ig_code),
                        "description": f"{ig_name} Interest Group Campus Lead",
                    },
                    {
                        "title": RoleType.IG_LEAD_ROLE(ig_code),
                        "description": f"{ig_name} Interest Group Lead",
                    },
                ]

                from db.user import Role
                for role_data in roles_to_ensure:
                    Role.objects.get_or_create(
                        title=role_data["title"],
                        defaults={
                            "id": str(uuid.uuid4()),
                            "description": role_data["description"],
                            "created_by_id": user_id,
                            "updated_by_id": user_id,
                        }
                    )

        return chapter


class CampusIGChapterUpdateSerializer(serializers.ModelSerializer):
    # Accept muid instead of UUID pk so the frontend can pass e.g. "john-doe@mulearn"
    lead = serializers.SlugRelatedField(
        slug_field="muid",
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = CampusIGChapter
        fields = ["description", "icon_link", "lead", "is_active"]

    def validate_lead(self, value):
        if value is None:
            return value
        org = self.instance.org
        if not validate_campus_member(value.id, org.id):
            raise serializers.ValidationError("The lead must be a member of this campus.")
        return value

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        new_lead = validated_data.get("lead")

        instance.description = validated_data.get("description", instance.description)
        instance.icon_link = validated_data.get("icon_link", instance.icon_link)
        instance.is_active = validated_data.get("is_active", instance.is_active)
        instance.updated_by_id = user_id

        # If lead changed, reassign campus IG lead role
        if new_lead and new_lead != instance.lead:
            success = assign_ig_campus_lead(instance, new_lead, user_id)
            if not success:
                raise serializers.ValidationError(
                    {"lead": "Could not transfer lead: the required IG campus lead role does not exist."}
                )
        else:
            instance.save()

        return instance


class CampusSocialLinkSerializer(serializers.ModelSerializer):

    class Meta:
        model = CampusSocialLink
        fields = ["id", "platform", "url"]


class CampusSocialLinkUpsertSerializer(serializers.Serializer):
    platform = serializers.CharField(max_length=30)
    url = serializers.URLField(max_length=500)

    def validate_platform(self, value):
        if value not in SocialPlatformType.get_all_values():
            raise serializers.ValidationError(
                f"Invalid platform. Must be one of: {', '.join(SocialPlatformType.get_all_values())}"
            )
        return value

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        org = self.context.get("org")

        try:
            social_link = CampusSocialLink.objects.get(
                org=org,
                platform=validated_data["platform"],
            )
            social_link.url = validated_data["url"]
            social_link.updated_by_id = user_id
            social_link.save()
        except CampusSocialLink.DoesNotExist:
            social_link = CampusSocialLink.objects.create(
                id=str(uuid.uuid4()),
                org=org,
                platform=validated_data["platform"],
                url=validated_data["url"],
                created_by_id=user_id,
                updated_by_id=user_id,
            )
        return social_link

class CampusLCListSerializer(serializers.ModelSerializer):
    ig_name = serializers.CharField(source="ig.name", default=None)
    member_count = serializers.IntegerField(default=0)
    meeting_count = serializers.IntegerField(default=0)
    last_meeting_time = serializers.DateTimeField(allow_null=True)

    class Meta:
        model = LearningCircle
        fields = ["id", "name", "ig_name", "member_count", "meeting_count", "last_meeting_time"]
        
    name = serializers.CharField(source="title")

class CampusLCMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source="user.id")
    full_name = serializers.CharField(source="user.full_name")
    muid = serializers.CharField(source="user.muid")
    karma = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()

    class Meta:
        model = UserCircleLink
        fields = ["user_id", "full_name", "muid", "karma", "level"]
        
    def get_karma(self, obj):
        return getattr(obj.user.wallet_user, 'karma', 0) if hasattr(obj.user, 'wallet_user') else 0
        
    def get_level(self, obj):
        level_link = obj.user.user_lvl_link_user.first()
        return level_link.level.name if level_link else None

class CampusIGListSerializer(serializers.ModelSerializer):
    campus_member_count = serializers.IntegerField(default=0)
    cover_image = serializers.ReadOnlyField()
    icon_image = serializers.ReadOnlyField()

    class Meta:
        model = InterestGroup
        fields = ["id", "name", "code", "campus_member_count", "cover_image", "icon_image"]

class CampusIGMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source="user.id")
    full_name = serializers.CharField(source="user.full_name")
    muid = serializers.CharField(source="user.muid")
    karma = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()

    class Meta:
        model = UserIgLink
        fields = ["user_id", "full_name", "muid", "karma", "level"]
        
    def get_karma(self, obj):
        return getattr(obj.user.wallet_user, 'karma', 0) if hasattr(obj.user, 'wallet_user') else 0
        
    def get_level(self, obj):
        level_link = obj.user.user_lvl_link_user.first()
        return level_link.level.name if level_link else None


class StudentActivityTimelineSerializer(serializers.ModelSerializer):
    task_name = serializers.CharField(source="task.title", read_only=True)
    ig_name = serializers.CharField(source="task.ig.name", read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = KarmaActivityLog
        fields = ["id", "task_name", "ig_name", "karma", "status", "created_at"]

    def get_status(self, obj):
        if obj.appraiser_approved:
            return "Approved"
        elif obj.appraiser_approved is False:
            return "Rejected"
        return "Pending"


class CampusShowcaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollegeShowcase
        fields = [
            "org_id",
            "about",
            "hero_image",
            "highlights",
            "gallery",
            "testimonials",
            "contact_email",
            "contact_phone",
            "updated_at"
        ]
        read_only_fields = ["org_id", "updated_at"]

    def create(self, validated_data):
        org_id = self.context.get("org_id")
        user_id = self.context.get("user_id")

        showcase, created = CollegeShowcase.objects.update_or_create(
            org_id=org_id,
            defaults={
                **validated_data,
                "updated_by_id": user_id,
                "created_by_id": user_id if not getattr(self, 'instance', None) else self.instance.created_by_id
            }
        )
        return showcase

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        if user_id:
            instance.updated_by_id = user_id
        return super().update(instance, validated_data)