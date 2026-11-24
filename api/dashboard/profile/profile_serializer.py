import uuid

from decouple import config as decouple_config
from django.core.cache import cache
from django.db import transaction
from django.db.models import F, Sum, Q, Case, When, Value, CharField, Exists, OuterRef
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from db.task import UserIgLvlLink
from db.organization import UserOrganizationLink, District
from db.task import (
    InterestGroup,
    KarmaActivityLog,
    Level,
    TaskList,
    Wallet,
    UserIgLink,
    UserLvlLink,
    UserIgLvlLink,
)
from db.user import User, UserSettings, Socials, UserRoleLink
from utils.exception import CustomException
from utils.permission import JWTUtils
from utils.types import (
    OrganizationType,
    RoleType,
    WebHookActions,
    WebHookCategory,
    UnitType,
)
from utils.utils import DateTimeUtils, DiscordWebhooks

BE_DOMAIN_NAME = decouple_config("BE_DOMAIN_NAME")


class UserLogSerializer(ModelSerializer):
    task_name = serializers.ReadOnlyField(source="task.title")
    created_date = serializers.CharField(source="created_at")

    class Meta:
        model = KarmaActivityLog
        fields = ["task_name", "karma", "created_date"]


class UserShareQrcode(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["profile_pic"]


class UserCoverPicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["cover_pic"]


def _rollup(rows, fields):
    """Sum karma over `rows` grouped by `fields`, highest karma first."""
    totals = {}
    for row in rows:
        key = tuple(row[field] for field in fields)
        totals[key] = totals.get(key, 0) + (row["karma"] or 0)
    return [
        dict(zip(fields, key), karma=karma)
        for key, karma in sorted(totals.items(), key=lambda item: -item[1])
    ]


def get_karma_breakdown(user_id):
    is_intern_creator = Exists(
        UserRoleLink.objects.filter(
            user=OuterRef("task__created_by"),
            role__title__in=[RoleType.INTERN.value, RoleType.INTERN_LEAD.value],
            is_active=True,
        )
    )

    # Priority order: Event > IG > Intern > General enablement (catch-all).
    # A task linked to an event is always bucketed as "event", even if the
    # event itself is IG-run (Event.organiser_ig/scope_ig) — the organizing
    # IG is surfaced as metadata on the event split entry instead, so karma
    # is never double-counted across buckets.
    bucket = Case(
        When(task__event_fk__isnull=False, then=Value("event")),
        When(task__ig__isnull=False, then=Value("ig")),
        When(
            Q(task__hashtag__startswith="#intern-") | Q(is_intern_creator=True),
            then=Value("intern"),
        ),
        default=Value("general"),
        output_field=CharField(),
    )

    # One query, grouped by every dimension the five breakdowns below need, then
    # rolled up in Python. This used to be five separate aggregate queries over
    # the same rows; a user's approved log is small, so the grouped result is too.
    rows = list(
        KarmaActivityLog.objects.filter(user_id=user_id, appraiser_approved=True)
        .annotate(is_intern_creator=is_intern_creator)
        .annotate(bucket=bucket)
        .values(
            "bucket",
            event_id=F("task__event_fk_id"),
            event_title=F("task__event_fk__title"),
            event_type=F("task__event_fk__event_type"),
            ig_id=F("task__ig_id"),
            ig_name=F("task__ig__name"),
            ig_code=F("task__ig__code"),
            category=F("task__type__title"),
            level_id=F("task__level_id"),
            level_name=F("task__level__name"),
        )
        .annotate(karma=Sum("karma"))
    )

    def in_bucket(name):
        return [row for row in rows if row["bucket"] == name]

    return {
        "events": _rollup(in_bucket("event"), ("event_id", "event_title", "event_type")),
        "ig": _rollup(in_bucket("ig"), ("ig_id", "ig_name", "ig_code")),
        "intern": {"karma": sum(row["karma"] or 0 for row in in_bucket("intern"))},
        "general": _rollup(in_bucket("general"), ("category",)),
        # Level breakdown cross-cuts all the buckets above — it sums karma by the
        # difficulty level tagged on the task itself, independent of whether the
        # task is an event/ig/intern/general task.
        "level": _rollup(rows, ("level_id", "level_name")),
    }


ACTIVE_USER_COUNT_CACHE_KEY = "profile:active_user_count"
ACTIVE_USER_COUNT_CACHE_TTL = 60 * 5


def get_active_user_count():
    """
    Total number of (non-suspended) users, used as the percentile denominator.

    A COUNT over the whole user table per profile view; it only moves when
    someone registers, so one fixed cache key with a short TTL is enough and no
    invalidation is needed (the percentile is at most a few minutes behind).
    """
    try:
        count = cache.get(ACTIVE_USER_COUNT_CACHE_KEY)
    except Exception:
        count = None
    if count is None:
        count = User.objects.all().count()
        try:
            cache.set(ACTIVE_USER_COUNT_CACHE_KEY, count, ACTIVE_USER_COUNT_CACHE_TTL)
        except Exception:
            pass
    return count


def get_karma_rank(user, roles):
    """
    Rank of `user` by karma within their peer group (mentors, enablers, or
    everyone else), or None when the user is not in that group.

    Ordering is karma desc, then wallet.updated_at desc, then created_at asc.
    This used to load the user_id of every wallet at or above the user's karma
    into Python and call list.index(); for a low-karma user that is most of the
    wallet table. The same position is now computed by counting the wallets
    that sort strictly ahead.
    """
    wallet = user.wallet_user
    ahead = (
        Q(karma__gt=wallet.karma)
        | Q(karma=wallet.karma, updated_at__gt=wallet.updated_at)
        | Q(
            karma=wallet.karma,
            updated_at=wallet.updated_at,
            created_at__lt=wallet.created_at,
        )
    )

    for role in (RoleType.MENTOR.value, RoleType.ENABLER.value):
        if role in roles:
            group = Wallet.objects.filter(
                user__user_role_link_user__verified=True,
                user__user_role_link_user__role__title=role,
            )
            if not group.filter(pk=wallet.pk).exists():
                return None
            return group.filter(ahead).values("user_id").distinct().count() + 1

    # Everyone else: all wallets except those of enablers and mentors.
    staff_links = UserRoleLink.objects.filter(
        role__title__in=[RoleType.ENABLER.value, RoleType.MENTOR.value]
    )
    if staff_links.filter(user_id=user.id).exists():
        return None
    # Counted as (all wallets ahead) - (staff wallets ahead) rather than with a
    # NOT EXISTS per wallet: the first count is a plain range scan on the karma
    # index, and the second starts from the few thousand staff role links and
    # looks each wallet up by its unique user_id.
    everyone_ahead = Wallet.objects.filter(ahead).count()
    staff_ahead = Wallet.objects.filter(
        ahead, user_id__in=staff_links.values("user_id")
    ).count()
    return everyone_ahead - staff_ahead + 1


class UserProfileSerializer(serializers.ModelSerializer):
    joined = serializers.DateTimeField(source="created_at")
    level = serializers.CharField(source="user_lvl_link_user.level.name", default=None)
    grit = serializers.IntegerField(source="user_lvl_link_user.grit", default=None)
    is_public = serializers.BooleanField(
        source="user_settings_user.is_public", default=None
    )
    karma = serializers.IntegerField(source="wallet_user.karma", default=None)
    roles = serializers.SerializerMethodField()
    role_verification = serializers.SerializerMethodField()
    lead_enabler_verified = serializers.SerializerMethodField()
    college_id = serializers.SerializerMethodField()
    college_code = serializers.SerializerMethodField()
    company_id = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    karma_distribution = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()
    org_district_id = serializers.SerializerMethodField()
    percentile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "joined",
            "full_name",
            "gender",
            "muid",
            "roles",
            "role_verification",
            "lead_enabler_verified",
            "college_id",
            "college_code",
            "company_id",
            "company_name",
            "org_district_id",
            "karma",
            "rank",
            "karma_distribution",
            "level",
            "grit",
            "profile_pic",
            "cover_pic",
            "interest_groups",
            "is_public",
            "percentile",
        )

    def _get_user_org_link(self, obj, org_type):
        # Cached per user and org type: a person can hold a college and a
        # company link at once (a Student who is also a Mentor), and one
        # serializer instance serves every row under many=True.
        cache = self.__dict__.setdefault("_user_org_links", {})
        key = (id(obj), org_type)
        if key not in cache:
            # Filter and order the prefetched links in Python. Calling
            # .filter().order_by() on the related manager discards the prefetch
            # (and its select_related("org")) and runs two more queries.
            links = [
                link
                for link in obj.user_organization_link_user.all()
                if link.org.org_type == org_type
            ]
            links.sort(key=lambda link: (link.created_at, link.id), reverse=True)
            cache[key] = links[0] if links else None
        return cache[key]

    def _college_link(self, obj):
        return self._get_user_org_link(obj, OrganizationType.COLLEGE.value)

    def _company_link(self, obj):
        return self._get_user_org_link(obj, OrganizationType.COMPANY.value)

    def get_percentile(self, obj):
        users_count_lt_user_karma = Wallet.objects.filter(
            karma__lt=obj.wallet_user.karma
        ).count()
        user_count = get_active_user_count()
        return (
            0
            if user_count == 0
            else 100 - ((users_count_lt_user_karma * 100) / user_count)
        )

    def get_roles(self, obj):
        if "role_values" in self.context:
            return self.context["role_values"]
        
        # Use explicitly prefetched roles to prevent lazy DB queries
        role_links = getattr(obj, "prefetched_roles", obj.user_role_link_user.all())
        role_values = list({link.role.title for link in role_links})
        
        self.context["role_values"] = role_values
        return role_values

    def get_role_verification(self, obj):
        role_links = getattr(obj, "prefetched_roles", obj.user_role_link_user.all())
        return [
            {
                "role": link.role.title,
                "is_verified": link.verified
            }
            for link in role_links
        ]

    # college_* is always the person's college, whatever their roles. It used
    # to switch to the company for anyone with the Mentor role, so a mentor's
    # college_id was a company id (opening it as a campus gave "campus not
    # found") and a Student who was also a Mentor lost their college.
    def get_college_id(self, obj):
        link = self._college_link(obj)
        return link.org.id if link else None

    def get_college_code(self, obj):
        link = self._college_link(obj)
        return link.org.code if link else None

    def get_company_id(self, obj):
        link = self._company_link(obj)
        return link.org.id if link else None

    def get_company_name(self, obj):
        link = self._company_link(obj)
        return link.org.title if link else None

    def get_org_district_id(self, obj):
        # The college's district (it seeds the college picker), else the
        # company's. district_id is already on the org row; going through
        # org.district loaded the District just to read its primary key.
        link = self._college_link(obj) or self._company_link(obj)
        return link.org.district_id if link else None

    def get_rank(self, obj):
        return get_karma_rank(obj, self.get_roles(obj))

    def get_karma_distribution(self, obj):
        return get_karma_breakdown(obj.id)

    def get_interest_groups(self, obj):
        # The user's currently selected IGs, from the links the view prefetched.
        selected_ig_ids = {
            link.ig_id
            for link in obj.user_ig_link_user.all()
            if link.is_active
            and link.assignment_type == UserIgLink.AssignmentType.LEARNER
        }
        if not selected_ig_ids:
            return []

        # Get level entries only for IGs the user currently has selected
        user_ig_levels = list(
            UserIgLvlLink.objects.filter(
                user=obj, ig_id__in=selected_ig_ids
            ).select_related('ig', 'level')
        )

        # IG-specific karma for all of those IGs in one grouped query (this was
        # one aggregate query per interest group).
        karma_by_ig = dict(
            KarmaActivityLog.objects.filter(
                user=obj,
                appraiser_approved=True,
                task__ig_id__in=[link.ig_id for link in user_ig_levels],
            )
            .values_list("task__ig_id")
            .annotate(total=Sum("karma"))
        ) if user_ig_levels else {}

        return [
            {
                "id": ig_level_link.ig.id,
                "name": ig_level_link.ig.name,
                "karma": karma_by_ig.get(ig_level_link.ig_id) or 0,
                "selected": ig_level_link.ig.id in selected_ig_ids,
                "level": {
                    "count": ig_level_link.level.level_order,
                    "unit": UnitType.LEVEL.value
                }
            }
            for ig_level_link in user_ig_levels
        ]

    def get_lead_enabler_verified(self, obj):
        role_links = getattr(obj, "prefetched_roles", obj.user_role_link_user.all())
        for link in role_links:
            role_title = getattr(getattr(link, "role", None), "title", None)
            if (
                role_title == RoleType.LEAD_ENABLER.value
                and getattr(link, "verified", False)
                and getattr(link, "is_active", False)
            ):
                return True
        return False


class UserLevelSerializer(serializers.ModelSerializer):
    tasks = serializers.SerializerMethodField()

    class Meta:
        model = Level
        fields = ("name", "tasks", "karma")

    # With many=True DRF reuses this one serializer instance for every level, so
    # the three lookups below are cached on it and run once per request instead
    # of once (or twice) per level.
    def _get_completed_tasks(self, user_id):
        if getattr(self, "completed_tasks", None) is None:
            self.completed_tasks = set(
                KarmaActivityLog.objects.filter(
                    user=user_id, appraiser_approved=True
                ).values_list("task_id", flat=True)
            )
        return self.completed_tasks

    def _get_user_ig_names(self, user_id):
        if getattr(self, "user_ig_names", None) is None:
            self.user_ig_names = set(
                UserIgLink.objects.filter(user__id=user_id).values_list(
                    "ig__name", flat=True
                )
            )
        return self.user_ig_names

    def _get_tasks_by_level(self):
        if getattr(self, "tasks_by_level", None) is None:
            self.tasks_by_level = {}
            # Ordered like the old per-level query read them (through the
            # level_id index, so by primary key within a level).
            for task in TaskList.objects.filter(level__isnull=False).select_related(
                "ig", "channel"
            ).order_by("level_id", "id"):
                self.tasks_by_level.setdefault(task.level_id, []).append(task)
        return self.tasks_by_level

    def get_tasks(self, obj):
        user_id = self.context.get("user_id")
        tasks = self._get_tasks_by_level().get(obj.id, [])

        if obj.level_order > 4:
            user_igs = self._get_user_ig_names(user_id)
            tasks = [task for task in tasks if task.ig and task.ig.name in user_igs]

        completed_tasks = self._get_completed_tasks(user_id)
        return [
            {
                "task_name": task.title,
                "discord_link": task.discord_link,
                "hashtag": task.hashtag,
                "active": task.active,
                "completed": is_completed,
                "karma": task.karma,
                "task_description": task.description,
                 # ig details
                 "interest_group": {
                    "id": task.ig.id if task.ig else None,
                    "name": task.ig.name if task.ig else None
                },
                # Submission Channel details
                "submission_channel": {
                    "id": task.channel.id if task.channel else None,
                    "name": task.channel.name if task.channel else None,
                    "discord_id": task.channel.discord_id if task.channel else None
                }
            }
            for task in tasks
            if (is_completed := (task.id in completed_tasks)) or task.active
        ]


class UserRankSerializer(ModelSerializer):
    full_name = serializers.CharField()
    role = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    karma = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("full_name", "role", "rank", "karma", "interest_groups")

    def get_role(self, obj):
        roles = self.context.get("roles")
        return ["Learner"] if len(roles) == 0 else roles

    def get_rank(self, obj):
        return get_karma_rank(obj, self.get_role(obj))

    def get_karma(self, obj):
        return total_karma.karma if (total_karma := obj.wallet_user) else None

    def get_interest_groups(self, obj):
        return [
            ig_link.ig.name
            for ig_link in UserIgLink.objects.filter(user=obj).select_related("ig")
        ]


# is public true then pass the qrcode vice versa delete the image
# another api when passing muid is give its corresponding image is returned
class ShareUserProfileUpdateSerializer(ModelSerializer):
    updated_by = serializers.CharField(required=False)
    updated_at = serializers.CharField(required=False)

    class Meta:
        model = UserSettings
        fields = ("is_public", "updated_by", "updated_at")

    def update(self, instance, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get("request"))
        instance.is_public = validated_data.get("is_public", instance.is_public)
        instance.updated_by_id = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance


class UserProfileEditSerializer(serializers.ModelSerializer):
    communities = serializers.ListField(write_only=True)
    district_id = serializers.PrimaryKeyRelatedField(
        queryset=District.objects.all(),
        source="district",
        write_only=True,
        required=False,
        allow_null=True,
    )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        communities = instance.user_organization_link_user.filter(
            org__org_type=OrganizationType.COMMUNITY.value
        ).all()
        data["communities"] = (
            [community.org_id for community in communities] if communities else []
        )

        district = instance.district
        if district:
            zone = district.zone
            state = zone.state if zone else None
            country = state.country if state else None
            data["district"] = {
                "id": district.id,
                "name": district.name,
                "state": {
                    "id": state.id if state else None,
                    "name": state.name if state else None,
                    "country": {
                        "id": country.id if country else None,
                        "name": country.name if country else None,
                    },
                },
            }
        else:
            data["district"] = None

        college_link = instance.user_organization_link_user.filter(
            org__org_type=OrganizationType.COLLEGE.value
        ).select_related("department").first()
        if college_link and college_link.department:
            data["department"] = {
                "id": college_link.department.id,
                "title": college_link.department.title,
            }
        else:
            data["department"] = None

        return data

    def update(self, instance, validated_data):
        with transaction.atomic():
            if "communities" in validated_data:
                community_data = validated_data.pop("communities", [])
                instance.user_organization_link_user.filter(
                    org__org_type=OrganizationType.COMMUNITY.value
                ).delete()
                user_organization_links = [
                    UserOrganizationLink(
                        id=uuid.uuid4(),
                        user=instance,
                        org_id=org_data,
                        created_by=instance,
                        created_at=DateTimeUtils.get_current_utc_time(),
                        verified=True,
                    )
                    for org_data in community_data
                ]

                UserOrganizationLink.objects.bulk_create(user_organization_links)

            return super().update(instance, validated_data)

    class Meta:
        model = User
        fields = [
            "full_name",
            "email",
            "mobile",
            "communities",
            "gender",
            "dob",
            "district_id",
        ]


class UserIgListSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterestGroup
        fields = [
            "id",
            "name",
        ]


class UserIgEditSerializer(serializers.ModelSerializer):
    interest_group = serializers.ListField(
        child=serializers.UUIDField(), write_only=True
    )

    def validate_interest_group(self, value):
        if len(value) > 3:
            raise serializers.ValidationError(
                "Cannot select more than 3 interest groups"
            )

        unique_ids = {str(ig_id) for ig_id in value}
        if len(unique_ids) != len(value):
            raise serializers.ValidationError(
                "Duplicate interest groups are not allowed"
            )

        existing_count = InterestGroup.objects.filter(id__in=unique_ids).count()
        if existing_count != len(unique_ids):
            raise serializers.ValidationError(
                "One or more interest groups are invalid"
            )

        return value

    def update(self, instance, validated_data):
        with transaction.atomic():
            ig_details = set(validated_data.pop("interest_group"))

            # Only remove LEARNER-type links; preserve MENTOR/LEAD/MODERATOR assignments.
            instance.user_ig_link_user.filter(
                assignment_type=UserIgLink.AssignmentType.LEARNER
            ).delete()
            user_ig_links = [
                UserIgLink(
                    id=uuid.uuid4(),
                    user=instance,
                    ig_id=ig_data,
                    created_by=instance,
                    created_at=DateTimeUtils.get_current_utc_time(),
                    assignment_type=UserIgLink.AssignmentType.LEARNER,
                    is_active=True,
                )
                for ig_data in ig_details
            ]
            UserIgLink.objects.bulk_create(user_ig_links)

            # Initialize IG levels (level 1) for the newly selected IGs, without
            # touching levels for IGs the user already had.
            if ig_details:
                level_1 = Level.objects.filter(level_order=1).first()
                if level_1:
                    existing_ig_ids = set(
                        UserIgLvlLink.objects.filter(
                            user=instance, ig_id__in=ig_details
                        ).values_list("ig_id", flat=True)
                    )
                    new_links = [
                        UserIgLvlLink(
                            id=uuid.uuid4(),
                            user=instance,
                            ig_id=ig_id,
                            level=level_1,
                            created_by=instance,
                            updated_by=instance,
                        )
                        for ig_id in ig_details
                        if str(ig_id) not in {str(i) for i in existing_ig_ids}
                    ]
                    if new_links:
                        UserIgLvlLink.objects.bulk_create(new_links)

            return super().update(instance, validated_data)

    class Meta:
        model = User
        fields = [
            "interest_group",
        ]


class LinkSocials(ModelSerializer):
    class Meta:
        model = Socials
        fields = [
            "github",
            "facebook",
            "instagram",
            "linkedin",
            "dribble",
            "behance",
            "stackoverflow",
            "medium",
            "hackerrank",
        ]

    def update(self, instance, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get("request"))

        def create_karma_activity_log(task_hashtag, karma_value):
            task = TaskList.objects.filter(hashtag=task_hashtag).first()
            if task:
                if karma_value > 0:
                    karma_log = KarmaActivityLog.objects.create(
                        task_id=task.id,
                        karma=karma_value,
                        user_id=user_id,
                        updated_by_id=user_id,
                        created_by_id=user_id,
                        peer_approved=True,
                        peer_approved_by_id=user_id,
                        appraiser_approved_by_id=user_id,
                        appraiser_approved=True,
                    )

                    value = karma_log.id
                    DiscordWebhooks.general_updates(
                        WebHookCategory.KARMA_INFO.value,
                        WebHookActions.UPDATE.value,
                        value,
                    )

                else:
                    karma_log = KarmaActivityLog.objects.filter(
                        task_id=task.id, user_id=user_id
                    ).first()
                    if karma_log is None:
                        # Nothing was awarded for this link, so there's
                        # nothing to take back.
                        return
                    karma_log.delete()
                Wallet.objects.filter(user_id=user_id).update(
                    karma=F("karma") + karma_value, updated_by_id=user_id
                )

        for account, account_url in validated_data.items():
            old_account_url = getattr(instance, account)
            if old_account_url != account_url:
                # no need of extra checking for "" if only None equivalent to empty social url
                if old_account_url in [None, ""] and account_url in [None, ""]:
                    pass
                elif old_account_url is None or old_account_url == "":
                    create_karma_activity_log(f"#social_{account}", 20)
                elif account_url is None or account_url == "":
                    create_karma_activity_log(f"#social_{account}", -20)

        return super().update(instance, validated_data)


class UserTermSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserSettings
        fields = [
            "is_userterms_approved",
            "user",
        ]

    def update(self, instance, validated_data):
        instance.is_userterms_approved = validated_data.get(
            "is_userterms_approved", instance.is_userterms_approved
        )
        instance.save()
        return instance



class ResetPasswordSerialzier(serializers.Serializer):
    current_password = serializers.CharField(required=True, allow_null=False)
    password = serializers.CharField(required=True, allow_null=False)

    class Meta:
        fields = ("current_password", "password")
        
        
class UserPermuteSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField()
    user_domains = serializers.SerializerMethodField()
    college_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["full_name", "user_domains", "college_name"]

    def get_user_domains(self, obj):
        return obj.user_domains.values_list("domain_name", flat=True)

    def _get_user_org_link(self, obj, org_type):
        if not hasattr(self, "user_org_link"):
            self.user_org_link = obj.user_organization_link_user.filter(
                org__org_type=org_type
            ).first()
        return self.user_org_link

    def _get_org_type(self, obj):
        return OrganizationType.COLLEGE.value

    def get_college_name(self, obj):
        org_type = self._get_org_type(obj)
        user_org_link = self._get_user_org_link(obj, org_type)
        return user_org_link.org.title if user_org_link and user_org_link.org else None
