import uuid

from decouple import config as decouple_config
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
    MainRoles,
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


class UserProfileSerializer(serializers.ModelSerializer):
    joined = serializers.DateTimeField(source="created_at")
    level = serializers.CharField(source="user_lvl_link_user.level.name", default=None)
    is_public = serializers.BooleanField(
        source="user_settings_user.is_public", default=None
    )
    karma = serializers.IntegerField(source="wallet_user.karma", default=None)
    roles = serializers.SerializerMethodField()
    role_verification = serializers.SerializerMethodField()
    lead_enabler_verified = serializers.SerializerMethodField()
    college_id = serializers.SerializerMethodField()
    college_code = serializers.SerializerMethodField()
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
            "org_district_id",
            "karma",
            "rank",
            "karma_distribution",
            "level",
            "profile_pic",
            "cover_pic",
            "interest_groups",
            "is_public",
            "percentile",
        )

    def _get_user_org_link(self, obj, org_type):
        if not getattr(self, "user_org_link", None):
            self.user_org_link = obj.user_organization_link_user.filter(
                org__org_type=org_type
            ).first()
        return self.user_org_link

    def _get_org_type(self, obj):
        roles = self.get_roles(obj)
        return (
            OrganizationType.COMPANY.value
            if MainRoles.MENTOR.value in roles
            else OrganizationType.COLLEGE.value
        )

    def get_percentile(self, obj):
        users_count_lt_user_karma = Wallet.objects.filter(
            karma__lt=obj.wallet_user.karma
        ).count()
        user_count = User.objects.all().count()
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

    def get_college_id(self, obj):
        org_type = self._get_org_type(obj)
        user_org_link = self._get_user_org_link(obj, org_type)
        return user_org_link.org.id if user_org_link else None

    def get_org_district_id(self, obj):
        org_type = self._get_org_type(obj)
        user_org_link = self._get_user_org_link(obj, org_type)
        return (
            user_org_link.org.district.id
            if user_org_link and hasattr(user_org_link.org, "district")
            else None
        )

    def get_college_code(self, obj):
        org_type = self._get_org_type(obj)
        if org_type == OrganizationType.COLLEGE.value:
            user_org_link = self._get_user_org_link(obj, org_type)
            return user_org_link.org.code if user_org_link else None
        return None

    def get_rank(self, obj):
        roles = self.get_roles(obj)
        user_karma = obj.wallet_user.karma
        if RoleType.MENTOR.value in roles:
            ranks = Wallet.objects.filter(
                user__user_role_link_user__verified=True,
                user__user_role_link_user__role__title=RoleType.MENTOR.value,
                karma__gte=user_karma,
            ).order_by("-karma", "-updated_at", "created_at")
        elif RoleType.ENABLER.value in roles:
            ranks = Wallet.objects.filter(
                user__user_role_link_user__verified=True,
                user__user_role_link_user__role__title=RoleType.ENABLER.value,
                karma__gte=user_karma,
            ).order_by("-karma", "-updated_at", "created_at")
        else:
            ranks = (
                Wallet.objects.filter(karma__gte=user_karma)
                .exclude(
                    Q(
                        user__user_role_link_user__role__title__in=[
                            RoleType.ENABLER.value,
                            RoleType.MENTOR.value,
                        ]
                    )
                )
                .order_by("-karma", "-updated_at", "created_at")
            )
        ranks = list(ranks.values_list("user_id", flat=True))
        return ranks.index(obj.id) + 1

    def get_karma_distribution(self, obj):
        # Exists subqueries to safely check creator's roles WITHOUT joining,
        # which would cause duplicate rows and multiply karma sums incorrectly.
        is_mentor = Exists(
            UserRoleLink.objects.filter(
                user=OuterRef("task__created_by"),
                role__title=RoleType.MENTOR.value
            )
        )
        is_intern = Exists(
            UserRoleLink.objects.filter(
                user=OuterRef("task__created_by"),
                role__title=RoleType.INTERN.value
            )
        )
        is_ig_lead = Exists(
            UserRoleLink.objects.filter(
                user=OuterRef("task__created_by"),
                role__title=RoleType.IG_LEAD.value
            )
        )

        return (
            KarmaActivityLog.objects.filter(user=obj, appraiser_approved=True)
            # Annotate role flags first (Exists = no join, no duplication)
            .annotate(
                is_mentor=is_mentor,
                is_intern=is_intern,
                is_ig_lead=is_ig_lead,
            )
            # Then bucket using priority order:
            # 1. Events Task  (task linked to an event)
            # 2. IG Task      (task linked to an IG, or creator is IG Lead)
            # 3. Mentor Task  (task created by a Mentor)
            # 4. Intern Task  (task created by an Intern)
            # 5. Other Task   (everything else)
            .annotate(
                bucket=Case(
                    When(task__event_fk__isnull=False, then=Value("Events Task")),
                    When(
                        Q(task__ig__isnull=False) | Q(is_ig_lead=True),
                        then=Value("IG Task")
                    ),
                    When(is_mentor=True, then=Value("Mentor Task")),
                    When(is_intern=True, then=Value("Intern Task")),
                    default=Value("Other Task"),
                    output_field=CharField()
                )
            )
            .values(task_type=F("bucket"))
            .annotate(karma=Sum("karma"))
            .order_by("-karma")
        )

    def get_interest_groups(self, obj):
        
        # Get all IGs where user has a level entry (has interacted with this IG)
        user_ig_levels = UserIgLvlLink.objects.filter(user=obj).select_related('ig', 'level')
        
        # Get user's currently selected IGs
        selected_ig_ids = set(
            UserIgLink.objects.filter(user=obj, is_active=True, assignment_type=UserIgLink.AssignmentType.LEARNER).values_list('ig_id', flat=True)
        )
        
        interest_groups = []
        for ig_level_link in user_ig_levels:
            # Calculate IG-specific karma
            total_ig_karma = (
                KarmaActivityLog.objects.filter(
                    task__ig=ig_level_link.ig, user=obj, appraiser_approved=True
                )
                .aggregate(Sum("karma"))
                .get("karma__sum") or 0
            )
            
            interest_groups.append({
                "id": ig_level_link.ig.id,
                "name": ig_level_link.ig.name,
                "karma": total_ig_karma,
                "selected": ig_level_link.ig.id in selected_ig_ids,
                "level": {
                    "count": ig_level_link.level.level_order,
                    "unit": UnitType.LEVEL.value
                }
            })
        
        return interest_groups
    
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

    def _get_completed_tasks(self, user_id):
        if getattr(self, "completed_tasks", None):
            return self.completed_tasks
        self.completed_tasks = list(
            KarmaActivityLog.objects.filter(user=user_id, appraiser_approved=True)
            .select_related("task__id")
            .values_list("task__id", flat=True)
        )
        return self.completed_tasks

    def get_tasks(self, obj):
        user_id = self.context.get("user_id")
        user_igs = (
            UserIgLink.objects.filter(user__id=user_id)
            .select_related("ig")
            .values_list("ig__name", flat=True)
        )
        tasks = TaskList.objects.filter(level=obj).select_related("ig","channel")

        if obj.level_order > 4:
            tasks = tasks.filter(ig__name__in=user_igs)

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
        roles = self.get_role(obj)
        user_karma = obj.wallet_user.karma
        if RoleType.MENTOR.value in roles:
            ranks = Wallet.objects.filter(
                user__user_role_link_user__verified=True,
                user__user_role_link_user__role__title=RoleType.MENTOR.value,
                karma__gte=user_karma,
            ).order_by("-karma", "-updated_at", "created_at")
        elif RoleType.ENABLER.value in roles:
            ranks = Wallet.objects.filter(
                user__user_role_link_user__verified=True,
                user__user_role_link_user__role__title=RoleType.ENABLER.value,
                karma__gte=user_karma,
            ).order_by("-karma", "-updated_at", "created_at")
        else:
            ranks = (
                Wallet.objects.filter(karma__gte=user_karma)
                .exclude(
                    Q(
                        user__user_role_link_user__role__title__in=[
                            RoleType.ENABLER.value,
                            RoleType.MENTOR.value,
                        ]
                    )
                )
                .order_by("-karma", "-updated_at", "created_at")
            )

        ranks = list(ranks.values_list("user_id", flat=True))
        return ranks.index(obj.id) + 1

    def get_karma(self, obj):
        return total_karma.karma if (total_karma := obj.wallet_user) else None

    def get_interest_groups(self, obj):
        return [ig_link.ig.name for ig_link in UserIgLink.objects.filter(user=obj)]


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
    interest_group = serializers.ListField(write_only=True)

    def update(self, instance, validated_data):
        with transaction.atomic():
            instance.user_ig_link_user.all().delete()
            ig_details = set(validated_data.pop("interest_group", []))
            user_ig_links = [
                UserIgLink(
                    id=uuid.uuid4(),
                    user=instance,
                    ig_id=ig_data,
                    created_by=instance,
                    created_at=DateTimeUtils.get_current_utc_time(),
                )
                for ig_data in ig_details
            ]
            if len(user_ig_links) > 3:
                raise CustomException("Cannot add more than 3 interest groups")
            UserIgLink.objects.bulk_create(user_ig_links)
            
            # Initialize IG levels for newly added IGs
            from django.db import connection
            for ig_id in ig_details:
                # Get level 1 ID
                with connection.cursor() as cursor:
                    cursor.execute("SELECT id FROM level WHERE level_order = 1 LIMIT 1")
                    level_1_id = cursor.fetchone()
                    if level_1_id:
                        # UPSERT: Insert level 1 if doesn't exist, do nothing if exists
                        cursor.execute("""
                            INSERT INTO user_ig_lvl_link (id, user_id, ig_id, level_id, created_by, created_at, updated_by, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE updated_at = updated_at
                        """, [
                            str(uuid.uuid4()),
                            str(instance.id),
                            str(ig_id),
                            level_1_id[0],
                            str(instance.id),
                            DateTimeUtils.get_current_utc_time(),
                            str(instance.id),
                            DateTimeUtils.get_current_utc_time()
                        ])
            
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
                    KarmaActivityLog.objects.filter(
                        task_id=task.id, user_id=user_id
                    ).first().delete()
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
