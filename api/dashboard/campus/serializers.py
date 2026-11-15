import uuid
from datetime import datetime, time, timedelta, timezone

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate
from django.db import transaction
from rest_framework import serializers

from db.organization import Organization, UserOrganizationLink, College, CollegeShowcase
from db.task import KarmaActivityLog, InterestGroup, UserIgLink
from db.campus import CampusIGChapter, CampusSocialLink
from db.user import User, UserRoleLink
from utils.types import OrganizationType
from utils.types import RoleType, SocialPlatformType
from utils.utils import DateTimeUtils
from .dash_campus_helper import validate_campus_member, assign_ig_campus_lead, ensure_ig_execom_catalog_entries
from db.events import Event
from db.learning_circle import LearningCircle, UserCircleLink

def get_college_karma_rank(org):
    """
    Position of a college when all colleges are ordered by total member karma.

    This used to pull one (org, user, karma) row for every verified college
    membership on the platform into Python and sum and sort them there, on every
    request. It now reads organization.cached_total_karma / cached_member_count,
    which mu_celery.org_aggregates_cron refreshes every 15 minutes, and counts
    the colleges that sort ahead (an index range scan on
    idx_organization_org_type_karma). The rank can therefore lag karma changes
    by up to 15 minutes. Ties keep the old order: the older college ranks first.

    Returns None for a college with no verified members, as before.
    """
    if org.org_type != OrganizationType.COLLEGE.value or not org.cached_member_count:
        return None
    ahead = Organization.objects.filter(
        org_type=OrganizationType.COLLEGE.value,
        cached_member_count__gt=0,
    ).filter(
        Q(cached_total_karma__gt=org.cached_total_karma)
        | Q(cached_total_karma=org.cached_total_karma, created_at__lt=org.created_at)
    )
    return ahead.count() + 1


class CampusDetailsPublicSerializer(serializers.ModelSerializer):
    org_id = serializers.ReadOnlyField(source="id")
    college_name = serializers.ReadOnlyField(source="title")
    campus_code = serializers.ReadOnlyField(source="code")
    campus_zone = serializers.ReadOnlyField(source="district.zone.name")
    total_karma = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    social_links = serializers.SerializerMethodField()
    campus_lead = serializers.SerializerMethodField()
    execom = serializers.SerializerMethodField()
    top_10_campus_leaderboard = serializers.SerializerMethodField()
    active_ig_chapters = serializers.SerializerMethodField()
    karma_by_cluster = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "org_id",
            "college_name",
            "campus_code",
            "campus_zone",
            "total_karma",
            "total_members",
            "active_members",
            "rank",
            "social_links",
            "campus_lead",
            "execom",
            "top_10_campus_leaderboard",
            "active_ig_chapters",
            "karma_by_cluster",
        ]

    def get_total_members(self, obj):
        return obj.user_organization_link_org.filter(verified=True).values('user').distinct().count()

    def get_active_members(self, obj):
        since = DateTimeUtils.get_current_utc_time() - timedelta(days=30)
        return obj.user_organization_link_org.filter(
            verified=True,
            user__wallet_user__karma_last_updated_at__gte=since
        ).values('user').distinct().count()

    def get_total_karma(self, obj):
        from db.task import Wallet
        users_in_org = obj.user_organization_link_org.filter(verified=True).values_list('user', flat=True)
        return Wallet.objects.filter(
            user__in=users_in_org
        ).aggregate(total_karma=Sum("karma"))["total_karma"] or 0

    def get_rank(self, obj):
        return get_college_karma_rank(obj)

    def get_social_links(self, obj):
        links = CampusSocialLink.objects.filter(org=obj)
        return CampusSocialLinkSerializer(links, many=True).data

    def get_campus_lead(self, obj):
        lead_link = UserRoleLink.objects.filter(
            user__user_organization_link_user__org=obj,
            user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            user__user_organization_link_user__verified=True,
            role__title=RoleType.CAMPUS_LEAD.value,
        ).select_related("user", "role").first()

        if not lead_link:
            return None

        user = lead_link.user
        return {
            "user_id": str(user.id),
            "full_name": user.full_name,
            "muid": user.muid,
            "profile_pic": str(user.profile_pic) if user.profile_pic else None,
            "role": lead_link.role.title,
        }

    def get_execom(self, obj):
        campus_user_ids = obj.user_organization_link_org.filter(
            verified=True
        ).values_list("user_id", flat=True)

        execom_links = UserRoleLink.objects.filter(
            user_id__in=campus_user_ids,
            role__is_execom_role=True,
        ).select_related("user", "role")

        return ExecomMemberSerializer(execom_links, many=True).data

    def get_top_10_campus_leaderboard(self, obj):
        from db.task import Wallet

        top_wallets = Wallet.objects.filter(
            user__user_organization_link_user__org=obj,
            user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            user__user_organization_link_user__verified=True,
        ).select_related("user").distinct().order_by("-karma", "created_at")[:10]

        return [
            {
                "rank": index + 1,
                "user_id": str(wallet.user.id),
                "full_name": wallet.user.full_name,
                "muid": wallet.user.muid,
                "profile_pic": str(wallet.user.profile_pic) if wallet.user.profile_pic else None,
                "karma": wallet.karma,
            }
            for index, wallet in enumerate(top_wallets)
        ]

    def get_active_ig_chapters(self, obj):
        chapters = list(
            CampusIGChapter.objects.filter(
                org=obj, is_active=True
            ).select_related("ig", "lead")
        )

        # Member counts for every chapter in one grouped query (this was one
        # COUNT(DISTINCT) query per chapter).
        member_counts = dict(
            UserIgLink.objects.filter(
                ig_id__in=[chapter.ig_id for chapter in chapters],
                is_active=True,
                assignment_type=UserIgLink.AssignmentType.LEARNER,
                user__user_organization_link_user__org=obj,
                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                user__user_organization_link_user__verified=True,
            )
            .values_list("ig_id")
            .annotate(member_count=Count("user", distinct=True))
        ) if chapters else {}

        return [
            {
                "ig_chapter_id": chapter.id,
                "ig_name": chapter.ig.name,
                "ig_code": chapter.ig.code,
                "lead": {
                    "user_id": str(chapter.lead.id),
                    "full_name": chapter.lead.full_name,
                    "muid": chapter.lead.muid,
                } if chapter.lead else None,
                "member_count": member_counts.get(chapter.ig_id, 0),
            }
            for chapter in chapters
        ]

    def get_karma_by_cluster(self, obj):
        from django.db.models import OuterRef, Subquery
        from collections import defaultdict
        from db.task import Wallet

        wallet_karma_sq = Wallet.objects.filter(
            user=OuterRef("pk")
        ).values("karma")[:1]

        primary_category_sq = (
            UserIgLink.objects.filter(
                user_id=OuterRef("pk"),
                is_active=True,
                assignment_type=UserIgLink.AssignmentType.LEARNER,
            )
            .order_by("created_at")
            .values("ig__category")[:1]
        )

        all_rows = (
            User.objects.filter(
                user_organization_link_user__org=obj,
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                user_organization_link_user__verified=True,
            )
            .annotate(
                user_karma=Subquery(wallet_karma_sq),
                primary_category=Subquery(primary_category_sq),
            )
            .values("id", "primary_category", "user_karma")
            .distinct()
        )

        category_map = defaultdict(lambda: {"total_karma": 0, "member_count": 0, "seen_users": set()})

        for row in all_rows:
            category = row["primary_category"] or "unclustered"
            user_id = row["id"]
            karma = row["user_karma"] or 0

            if user_id not in category_map[category]["seen_users"]:
                category_map[category]["seen_users"].add(user_id)
                category_map[category]["total_karma"] += karma
                category_map[category]["member_count"] += 1

        return {
            category: {
                "total_karma": data["total_karma"],
                "member_count": data["member_count"],
            }
            for category, data in category_map.items()
        }


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
        return get_college_karma_rank(obj.org)

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
    full_name = serializers.SerializerMethodField()
    muid = serializers.CharField()
    karma = serializers.IntegerField()
    rank = serializers.SerializerMethodField()
    level = serializers.CharField()
    # is_active = serializers.CharField()
    join_date = serializers.CharField()
    last_karma_gained = serializers.CharField()
    graduation_year = serializers.CharField()
    department = serializers.CharField()
    is_alumni = serializers.BooleanField()
    ig_count = serializers.IntegerField(default=0)
    lc_count = serializers.IntegerField(default=0)

    class Meta:
        fields = (
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

        # One grouped query for the whole week instead of one aggregate per day.
        # The window is expressed as a datetime range (UTC, same as the
        # created_at__date lookups it replaces) so an index on created_at is usable.
        window_start = datetime.combine(date_range[-1], time.min, tzinfo=timezone.utc)
        window_end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=timezone.utc)
        karma_by_day = dict(
            KarmaActivityLog.objects.filter(
                user_id__in=member_user_ids,
                created_at__gte=window_start,
                created_at__lt=window_end,
                appraiser_approved=True,
            )
            .annotate(day=TruncDate("created_at", tzinfo=timezone.utc))
            .values_list("day")
            .annotate(karma=Sum("karma"))
        )

        for date in date_range:
            response[str(date)] = karma_by_day.get(date) or 0

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

        link, created = UserRoleLink.objects.get_or_create(
            user=validated_data["user"],
            role=validated_data["role"],
            defaults={
                "id": str(uuid.uuid4()),
                "created_by_id": user_id,
                "verified": True,
            }
        )
        if not created:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("User already has this role.")
        return link


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
        # IG campus lead/co-lead roles use canonical format: "{ig_code} CampusIGLead" / "{ig_code} CampusIGCoLead"
        for suffix in ("CampusIGLead", "CampusIGCoLead"):
            if title.endswith(suffix):
                ig_name = title[: -len(suffix)].strip()
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
    co_lead_id = serializers.ReadOnlyField(source="co_lead.id")
    co_lead_name = serializers.SerializerMethodField()
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
            "co_lead_id",
            "co_lead_name",
            "description",
            "icon_link",
            "is_active",
            "campus_ig_member_count",
        ]

    def get_lead_name(self, obj):
        if obj.lead:
            return obj.lead.full_name
        return None

    def get_co_lead_name(self, obj):
        if obj.co_lead:
            return obj.co_lead.full_name
        return None

    def _member_counts(self):
        """{(org_id, ig_id): learners} for every chapter being serialized, built once."""
        if getattr(self, "_counts", None) is None:
            instance = self.root.instance
            chapters = (
                [instance] if isinstance(instance, CampusIGChapter) else list(instance or [])
            )
            rows = UserIgLink.objects.filter(
                ig_id__in={chapter.ig_id for chapter in chapters},
                is_active=True,
                assignment_type=UserIgLink.AssignmentType.LEARNER,
                user__user_organization_link_user__org_id__in={
                    chapter.org_id for chapter in chapters
                },
                user__user_organization_link_user__verified=True,
            ).values_list(
                "user__user_organization_link_user__org_id", "ig_id"
            ).annotate(member_count=Count("user", distinct=True)) if chapters else []
            self._counts = {(org_id, ig_id): count for org_id, ig_id, count in rows}
        return self._counts

    def get_campus_ig_member_count(self, obj):
        # One grouped query for the page instead of one COUNT per chapter.
        return self._member_counts().get((obj.org_id, obj.ig_id), 0)


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

            ig_name = chapter.ig.name
            ig_code = chapter.ig.code

            # Populate the global role directory with this IG's assignable titles
            # immediately on chapter creation, regardless of whether a lead is set yet.
            ensure_ig_execom_catalog_entries(ig_code, ig_name, user_id)

            if chapter.lead:
                # assign_ig_campus_lead handles bootstrapping the roles internally
                assign_ig_campus_lead(chapter, chapter.lead, user_id)
            else:
                # Ensure IG roles exist in the database
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
                        "title": RoleType.IG_CAMPUS_COLEAD_ROLE(ig_code),
                        "description": f"{ig_name} Interest Group Campus Co-Lead",
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
        level_link = getattr(obj.user, "user_lvl_link_user", None)
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
        level_link = getattr(obj.user, "user_lvl_link_user", None)
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