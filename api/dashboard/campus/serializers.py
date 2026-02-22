import uuid
from datetime import timedelta

from django.db.models import Sum, Count, F
from rest_framework import serializers

from db.campus import CampusExecom, CampusExecomRole, CampusIGChapter, CampusSocialLink
from db.organization import Organization, UserOrganizationLink, College
from db.task import KarmaActivityLog, InterestGroup
from db.user import User, UserRoleLink
from utils.types import OrganizationType
from utils.types import RoleType
from utils.utils import DateTimeUtils


# ── Existing serializers (preserved) ──────────────────────────────


class CampusDetailsPublicSerializer(serializers.ModelSerializer):
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
        return obj.user_organization_link_org.count()

    def get_active_members(self, obj):
        last_month = DateTimeUtils.get_current_utc_time() - timedelta(weeks=26)
        return obj.user_organization_link_org.filter(
            verified=True,
            user__wallet_user__isnull=False,
            user__wallet_user__karma_last_updated_at__gte=last_month,
        ).count()

    def get_total_karma(self, obj):
        return (
            obj.user_organization_link_org.filter(
                org__org_type=OrganizationType.COLLEGE.value,
                verified=True,
                user__wallet_user__isnull=False,
            ).aggregate(total_karma=Sum("user__wallet_user__karma"))["total_karma"]
            or 0
        )

    def get_rank(self, obj):
        org_karma_dict = (
            UserOrganizationLink.objects.filter(
                org__org_type=OrganizationType.COLLEGE.value
            )
            .values("org")
            .annotate(total_karma=Sum("user__wallet_user__karma"))
        ).order_by("-total_karma", "org__created_at")

        rank_dict = {
            data["org"]: data["total_karma"] if data["total_karma"] is not None else 0
            for data in org_karma_dict
        }

        sorted_rank_dict = dict(
            sorted(rank_dict.items(), key=lambda x: x[1], reverse=True)
        )

        if obj.id in sorted_rank_dict:
            keys_list = list(sorted_rank_dict.keys())
            position = keys_list.index(obj.id)
            return position + 1

    def get_social_links(self, obj):
        return list(
            CampusSocialLink.objects.filter(org=obj).values("platform", "url", "label")
        )


class CampusDetailsSerializer(serializers.ModelSerializer):
    college_name = serializers.ReadOnlyField(source="org.title")
    campus_code = serializers.ReadOnlyField(source="org.code")
    campus_zone = serializers.ReadOnlyField(source="org.district.zone.name")
    campus_level = serializers.SerializerMethodField()
    total_karma = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()

    lead = serializers.SerializerMethodField()
    karma_rate_30d = serializers.SerializerMethodField()
    karma_rate_7d = serializers.SerializerMethodField()
    campus_ig_count = serializers.SerializerMethodField()
    ig_leads = serializers.SerializerMethodField()
    ig_chapters = serializers.SerializerMethodField()
    social_links = serializers.SerializerMethodField()

    class Meta:
        model = UserOrganizationLink
        fields = [
            "college_name",
            "campus_code",
            "campus_zone",
            "campus_level",
            "total_karma",
            "total_members",
            "active_members",
            "rank",
            "lead",
            "karma_rate_30d",
            "karma_rate_7d",
            "campus_ig_count",
            "ig_leads",
            "ig_chapters",
            "social_links",
        ]

    def get_lead(self, obj):

        campus_lead = User.objects.filter(
            user_organization_link_user__org=obj.org,
            user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            user_role_link_user__role__title=RoleType.CAMPUS_LEAD.value,
        ).first()
        if campus_lead:
            campus_lead = campus_lead.full_name

        enabler = User.objects.filter(
            user_organization_link_user__org=obj.org,
            user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
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
        return obj.org.user_organization_link_org.count()

    def get_active_members(self, obj):

        last_month = DateTimeUtils.get_current_utc_time() - timedelta(
            weeks=26
        )  # 6months
        return obj.org.user_organization_link_org.filter(
            verified=True,
            user__wallet_user__isnull=False,
            user__wallet_user__karma_last_updated_at__gte=last_month,
        ).count()

    def get_total_karma(self, obj):
        return (
            obj.org.user_organization_link_org.filter(
                org__org_type=OrganizationType.COLLEGE.value,
                verified=True,
                user__wallet_user__isnull=False,
            ).aggregate(total_karma=Sum("user__wallet_user__karma"))["total_karma"]
            or 0
        )

    def get_rank(self, obj):
        org_karma_dict = (
            UserOrganizationLink.objects.filter(
                org__org_type=OrganizationType.COLLEGE.value
            )
            .values("org")
            .annotate(total_karma=Sum("user__wallet_user__karma"))
        ).order_by("-total_karma", "org__created_at")

        rank_dict = {
            data["org"]: data["total_karma"] if data["total_karma"] is not None else 0
            for data in org_karma_dict
        }

        sorted_rank_dict = dict(
            sorted(rank_dict.items(), key=lambda x: x[1], reverse=True)
        )

        if obj.org.id in sorted_rank_dict:
            keys_list = list(sorted_rank_dict.keys())
            position = keys_list.index(obj.org.id)
            return position + 1

    # ── New fields added for campus dashboard ──

    def get_karma_rate_30d(self, obj):
        thirty_days_ago = DateTimeUtils.get_current_utc_time() - timedelta(days=30)
        return (
            KarmaActivityLog.objects.filter(
                user__user_organization_link_user__org=obj.org,
                created_at__gte=thirty_days_ago,
            ).aggregate(total=Sum("karma"))["total"]
            or 0
        )

    def get_karma_rate_7d(self, obj):
        seven_days_ago = DateTimeUtils.get_current_utc_time() - timedelta(days=7)
        return (
            KarmaActivityLog.objects.filter(
                user__user_organization_link_user__org=obj.org,
                created_at__gte=seven_days_ago,
            ).aggregate(total=Sum("karma"))["total"]
            or 0
        )

    def get_campus_ig_count(self, obj):
        return CampusIGChapter.objects.filter(org=obj.org, is_active=True).count()

    def get_ig_leads(self, obj):
        chapters = CampusIGChapter.objects.select_related(
            "lead_user", "ig"
        ).filter(org=obj.org, is_active=True, lead_user__isnull=False)
        return [
            {
                "full_name": ch.lead_user.full_name,
                "muid": ch.lead_user.muid,
                "profile_pic": getattr(ch.lead_user, "profile_pic", None),
                "ig_name": ch.ig.name,
            }
            for ch in chapters
        ]

    def get_ig_chapters(self, obj):
        chapters = CampusIGChapter.objects.select_related(
            "ig", "lead_user"
        ).filter(org=obj.org)
        return [
            {
                "id": ch.id,
                "ig_id": ch.ig_id,
                "ig_name": ch.ig.name,
                "ig_cluster": ch.ig.cluster,
                "lead_name": ch.lead_user.full_name if ch.lead_user else None,
                "is_active": ch.is_active,
            }
            for ch in chapters
        ]

    def get_social_links(self, obj):
        return list(
            CampusSocialLink.objects.filter(org=obj.org).values(
                "platform", "url", "label"
            )
        )


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
        )

    def get_rank(self, obj):
        ranks = self.context.get("ranks")
        return ranks.get(obj.id, None)

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

        for date in date_range:
            karma_logs = KarmaActivityLog.objects.filter(
                user__user_organization_link_user__org=instance,
                created_at__date=date,
            ).aggregate(
                karma=Sum("karma"),
            )
            response[str(date)] = karma_logs.get("karma", 0)

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


# ── New serializers for campus dashboard ──────────────────────────


class CampusLeaderboardSerializer(serializers.Serializer):
    """Leaderboard list items with computed rank."""
    user_id = serializers.CharField()
    full_name = serializers.SerializerMethodField()
    muid = serializers.CharField()
    profile_pic = serializers.CharField(allow_null=True)
    karma = serializers.IntegerField()
    rank = serializers.SerializerMethodField()
    level = serializers.CharField()
    join_date = serializers.CharField()
    last_karma_at = serializers.CharField()
    graduation_year = serializers.CharField(allow_null=True)
    department = serializers.CharField(allow_null=True)
    is_alumni = serializers.BooleanField()
    ig_count = serializers.IntegerField()

    def get_rank(self, obj):
        ranks = self.context.get("ranks", {})
        return ranks.get(obj.id, None)

    def get_full_name(self, obj):
        return obj.full_name


class CampusEventListSerializer(serializers.Serializer):
    """Campus event feed items."""
    id = serializers.CharField()
    title = serializers.CharField()
    slug = serializers.CharField()
    cover_image = serializers.CharField(allow_null=True)
    event_type = serializers.CharField()
    scope = serializers.SerializerMethodField()
    status = serializers.CharField()
    start_datetime = serializers.DateTimeField()
    end_datetime = serializers.DateTimeField()
    venue_type = serializers.SerializerMethodField()
    venue_city = serializers.SerializerMethodField()
    interest_count = serializers.IntegerField()
    is_featured = serializers.BooleanField()
    tags = serializers.SerializerMethodField()
    organizer = serializers.SerializerMethodField()

    def get_scope(self, obj):
        scope = getattr(obj, 'event_scope', None)
        if scope:
            return scope.scope
        return None

    def get_venue_type(self, obj):
        venue = getattr(obj, 'venue', None)
        if venue:
            return venue.venue_type
        return None

    def get_venue_city(self, obj):
        venue = getattr(obj, 'venue', None)
        if venue:
            return venue.city
        return None

    def get_tags(self, obj):
        return list(obj.tag_links.values_list('tag__name', flat=True))

    def get_organizer(self, obj):
        organiser = getattr(obj, 'organiser', None)
        if organiser is None:
            return None
        org_type = organiser.organiser_type
        name = None
        logo = None
        if organiser.org_id:
            name = organiser.org_id.title if hasattr(organiser.org_id, 'title') else None
        elif organiser.ig_id:
            name = organiser.ig_id.name if hasattr(organiser.ig_id, 'name') else None
        elif organiser.ci_org_id:
            name = organiser.ci_org_id.title if hasattr(organiser.ci_org_id, 'title') else None
        return {"type": org_type, "name": name, "logo": logo}


class ExecomMemberSerializer(serializers.ModelSerializer):
    """Execom list — user info + campus execom role title."""
    execom_id = serializers.CharField(source="id")
    user_id = serializers.CharField(source="user.id")
    full_name = serializers.SerializerMethodField()
    muid = serializers.CharField(source="user.muid")
    profile_pic = serializers.SerializerMethodField()
    role_id = serializers.CharField(source="role.id")
    role_title = serializers.CharField(source="role.title")

    class Meta:
        model = CampusExecom
        fields = ["execom_id", "user_id", "full_name", "muid", "profile_pic", "role_id", "role_title"]

    def get_full_name(self, obj):
        return obj.user.full_name

    def get_profile_pic(self, obj):
        return getattr(obj.user, "profile_pic", None)


class ExecomAddSerializer(serializers.Serializer):
    """Input validation for execom addition."""
    user_muid = serializers.CharField()
    role_id = serializers.CharField()


class CampusIGChapterSerializer(serializers.ModelSerializer):
    """Chapter list with IG and lead details."""
    ig = serializers.SerializerMethodField()
    lead = serializers.SerializerMethodField()
    member_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = CampusIGChapter
        fields = [
            "id",
            "ig",
            "lead",
            "is_active",
            "member_count",
            "created_at",
        ]

    def get_ig(self, obj):
        ig = obj.ig
        return {
            "id": ig.id,
            "name": ig.name,
            "cluster": ig.cluster,
            "icon": ig.icon,
        }

    def get_lead(self, obj):
        if obj.lead_user is None:
            return None
        return {
            "user_id": obj.lead_user.id,
            "full_name": obj.lead_user.full_name,
            "muid": obj.lead_user.muid,
        }


class CampusIGChapterWriteSerializer(serializers.Serializer):
    """Input validation for chapter create/update."""
    ig_id = serializers.CharField(required=False)
    lead_user_muid = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)


class CampusSocialLinkSerializer(serializers.ModelSerializer):
    """Social links list and write."""

    class Meta:
        model = CampusSocialLink
        fields = ["id", "platform", "url", "label"]
