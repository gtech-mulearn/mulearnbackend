import uuid

from django.db import transaction
from django.db.models import F, Sum, Q
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from db.organization import UserOrganizationLink
from db.task import InterestGroup, KarmaActivityLog, Level, TaskList, Wallet, UserIgLink, UserLvlLink
from db.user import User, UserSettings, Socials
from utils.exception import CustomException
from utils.permission import JWTUtils
from utils.types import OrganizationType, RoleType, MainRoles
from utils.utils import DateTimeUtils
from django.core.files.storage import FileSystemStorage
from decouple import config as decouple_config

BE_DOMAIN_NAME = decouple_config('BE_DOMAIN_NAME')

class UserLogSerializer(ModelSerializer):
    task_name = serializers.ReadOnlyField(source="task.title")
    created_date = serializers.CharField(source="created_at")

    class Meta:
        model = KarmaActivityLog
        fields = ["task_name", "karma", "created_date"]


class UserShareQrcode(serializers.ModelSerializer):  
    profile_pic = serializers.SerializerMethodField()
    class Meta:
        model = User  
        fields = ['profile_pic'] 


    def get_profile_pic(self,obj):
        # Here the media url in settings.py is /home/mishal/../../uid.png
        fs = FileSystemStorage()
        path = f'user/qr/{obj.id}.png'
        if fs.exists(path):
            qrcode_image = f"{self.context.get('request').build_absolute_uri('/')}{fs.url(path)[1:]}"
        else:
            return None  
        return qrcode_image

class UserProfileSerializer(serializers.ModelSerializer):
    joined = serializers.DateTimeField(source="created_at")
    level = serializers.CharField(source="user_lvl_link_user.level.name", default=None)
    is_public = serializers.BooleanField(source="user_settings_user.is_public", default=None)
    karma = serializers.IntegerField(source="wallet_user.karma", default=None)
    roles = serializers.SerializerMethodField()
    college_id = serializers.SerializerMethodField()
    college_code = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    karma_distribution = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()
    org_district_id = serializers.SerializerMethodField()
    profile_pic = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "joined",
            "first_name",
            "last_name",
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
        )
    
    def get_profile_pic(self,obj):
        fs = FileSystemStorage()
        path = f'user/profile/{obj.id}.png'
        if fs.exists(path):
            profile_pic = f"{BE_DOMAIN_NAME}{fs.url(path)}"
        else:
            profile_pic = obj.profile_pic
        return profile_pic
    
    def get_roles(self, obj):
        return list({link.role.title for link in obj.user_role_link_user.all()})

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
        org_type = OrganizationType.COMPANY.value if MainRoles.MENTOR.value in self.get_roles(
            obj) else OrganizationType.COLLEGE.value
        user_org_link = obj.user_organization_link_user.filter(org__org_type=org_type).first()
        return user_org_link.org.district.id if user_org_link and hasattr(user_org_link.org, 'district') else None

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
                user__user_role_link_user__role__title=RoleType.MENTOR.value,
                karma__gte=user_karma,
            ).count()
        elif RoleType.ENABLER.value in roles:
            ranks = Wallet.objects.filter(
                user__user_role_link_user__role__title=RoleType.ENABLER.value,
                karma__gte=user_karma,
            ).count()
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
                .count()
            )
        return ranks if ranks > 0 else None

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

    def get_tasks(self, obj):
        user_id = self.context.get("user_id")
        user_lvl = UserLvlLink.objects.filter(user__id=user_id).first().level.level_order
        user_igs = UserIgLink.objects.filter(user__id=user_id).values_list("ig__name", flat=True)
        tasks = TaskList.objects.filter(level=obj)

        data = []
        for task in tasks:
            completed = KarmaActivityLog.objects.filter(user=user_id, task=task, appraiser_approved=True).exists()
            if task.active or completed:
                data.append(
                    {
                        "task_name": task.title,
                        "discord_link": task.discord_link,
                        "hashtag": task.hashtag,
                        "completed": completed,
                        "karma": task.karma,
                    }
                )
        return data


class UserRankSerializer(ModelSerializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    role = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    karma = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("first_name", "last_name", "role", "rank", "karma", "interest_groups")

    def get_role(self, obj):
        roles = self.context.get("roles")
        return ["Learner"] if len(roles) == 0 else roles

    def get_rank(self, obj):
        roles = self.context.get("roles")
        user_karma = obj.wallet_user.karma
        if RoleType.MENTOR.value in roles:
            ranks = Wallet.objects.filter(
                user__user_role_link_user__role__title=RoleType.MENTOR.value,
                karma__gte=user_karma,
            ).count()
        elif RoleType.ENABLER.value in roles:
            ranks = Wallet.objects.filter(
                user__user_role_link_user__role__title=RoleType.ENABLER.value,
                karma__gte=user_karma,
            ).count()
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
                .count()
            )
        return ranks if ranks > 0 else None

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
            "first_name",
            "last_name",
            "email",
            "mobile",
            "communities",
            "gender",
            "dob",
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
            "hackerrank"
        ]

    def update(self, instance, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get("request"))
        accounts = [
            "github",
            "facebook",
            "instagram",
            "linkedin",
            "dribble",
            "behance",
            "stackoverflow",
            "medium",
            "hackerrank"
        ]

        old_accounts = {account: getattr(instance, account) for account in accounts}

        for account in accounts:
            setattr(
                instance, account, validated_data.get(account, old_accounts[account])
            )

        def create_karma_activity_log(task_title, karma_value):
            task = TaskList.objects.filter(title=task_title).first()
            if task:
                KarmaActivityLog.objects.create(
                    task_id=task.id,
                    karma=karma_value,
                    user_id=user_id,
                    updated_by_id=user_id,
                    created_by_id=user_id,
                )

        for account, account_url in validated_data.items():
            old_account_url = old_accounts[account]
            if account_url != old_account_url:
                if old_account_url is None:
                    create_karma_activity_log(f"social_{account}", 50)
                elif account_url is None:
                    create_karma_activity_log(f"social_{account}", -50)

        instance.save()
        return instance
