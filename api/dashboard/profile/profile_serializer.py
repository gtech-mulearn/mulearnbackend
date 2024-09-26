import uuid

from decouple import config as decouple_config
from django.db import transaction
from django.db.models import F, Sum, Q
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from db.organization import UserOrganizationLink, District
from db.task import (
    InterestGroup,
    KarmaActivityLog,
    Level,
    TaskList,
    Wallet,
    UserIgLink,
    UserLvlLink,
)
from db.user import User, UserSettings, Socials
from utils.exception import CustomException
from utils.permission import JWTUtils
from utils.types import (
    OrganizationType,
    RoleType,
    MainRoles,
    WebHookActions,
    WebHookCategory,
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


class UserProfileSerializer(serializers.ModelSerializer):
    joined = serializers.DateTimeField(source="created_at")
    level = serializers.CharField(source="user_lvl_link_user.level.name", default=None)
    is_public = serializers.BooleanField(
        source="user_settings_user.is_public", default=None
    )
    karma = serializers.IntegerField(source="wallet_user.karma", default=None)
    roles = serializers.SerializerMethodField()
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
            "college_id",
            "college_code",
            "org_district_id",
            "karma",
            "rank",
            "karma_distribution",
            "level",
            "profile_pic",
            "interest_groups",
            "is_public",
            "percentile",
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
        return list(
            {link.role.title for link in obj.user_role_link_user.filter(verified=True)}
        )

    def get_college_id(self, obj):
        org_type = (
            OrganizationType.COMPANY.value
            if MainRoles.MENTOR.value in self.get_roles(obj)
            else OrganizationType.COLLEGE.value
        )
        user_org_link = obj.user_organization_link_user.filter(
            org__org_type=org_type
        ).first()
        return user_org_link.org.id if user_org_link else None

    def get_org_district_id(self, obj):
        org_type = (
            OrganizationType.COMPANY.value
            if MainRoles.MENTOR.value in self.get_roles(obj)
            else OrganizationType.COLLEGE.value
        )
        user_org_link = obj.user_organization_link_user.filter(
            org__org_type=org_type
        ).first()
        return (
            user_org_link.org.district.id
            if user_org_link and hasattr(user_org_link.org, "district")
            else None
        )

    def get_college_code(self, obj):
        if user_org_link := obj.user_organization_link_user.filter(
            org__org_type=OrganizationType.COLLEGE.value
        ).first():
            return user_org_link.org.code
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
                .order_by("-karma")
            )

        for count, _rank in enumerate(ranks, start=1):
            if obj.id == _rank.user_id:
                return count

    def get_karma_distribution(self, obj):
        return (
            KarmaActivityLog.objects.filter(user=obj, appraiser_approved=True)
            .values(task_type=F("task__type__title"))
            .annotate(karma=Sum("karma"))
            .order_by()
        )

    def get_interest_groups(self, obj):
        interest_groups = []
        for ig_link in UserIgLink.objects.filter(user=obj):
            total_ig_karma = (
                0
                if KarmaActivityLog.objects.filter(
                    task__ig=ig_link.ig, user=obj, appraiser_approved=True
                )
                .aggregate(Sum("karma"))
                .get("karma__sum")
                is None
                else KarmaActivityLog.objects.filter(
                    task__ig=ig_link.ig, user=obj, appraiser_approved=True
                )
                .aggregate(Sum("karma"))
                .get("karma__sum")
            )
            interest_groups.append(
                {"id": ig_link.ig.id, "name": ig_link.ig.name, "karma": total_ig_karma}
            )
        return interest_groups


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
        user_igs = UserIgLink.objects.filter(user__id=user_id).values_list(
            "ig__name", flat=True
        )
        tasks = TaskList.objects.filter(level=obj)

        if obj.level_order > 4:
            tasks = tasks.filter(ig__name__in=user_igs)

        completed_tasks = self._get_completed_tasks(user_id)
        return [
            {
                "task_name": task.title,
                "discord_link": task.discord_link,
                "hashtag": task.hashtag,
                "completed": is_completed,
                "karma": task.karma,
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
                .order_by("-karma")
            )

        for count, _rank in enumerate(ranks, start=1):
            if obj.id == _rank.user_id:
                return count

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
            data["district"] = district.name
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
            "district",
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
