from django.db.models import Sum, F, Q
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from db.task import KarmaActivityLog, TotalKarma, UserIgLink, UserLvlLink, Level, TaskList
from db.user import User, UserSettings
from utils.permission import JWTUtils
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils


class UserLogSerializer(ModelSerializer):
    task_name = serializers.ReadOnlyField(source='task.title')
    created_date = serializers.CharField(source='created_at')

    class Meta:
        model = KarmaActivityLog
        fields = ["task_name", "karma", "created_date"]


class UserProfileSerializer(serializers.ModelSerializer):
    joined = serializers.DateTimeField(source="created_at")
    muid = serializers.CharField(source="mu_id")
    roles = serializers.SerializerMethodField()
    college_code = serializers.SerializerMethodField()
    karma = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    karma_distribution = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()
    is_public = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'joined', 'first_name', 'last_name', 'gender', 'muid', 'roles', 'college_code', 'karma', 'rank',
            'karma_distribution', 'level', 'profile_pic', 'interest_groups', 'is_public'
        )

    def get_is_public(self, obj):
        is_public_status = UserSettings.objects.filter(
            user=obj).first().is_public
        return is_public_status

    def get_roles(self, obj):
        return list(obj.user_role_link_user.values_list('role__title', flat=True))

    def get_college_code(self, obj):
        user_org_link = obj.user_organization_link_user_id.filter(
            org__org_type=OrganizationType.COLLEGE.value).first()
        if user_org_link:
            return user_org_link.org.code
        return None

    def get_karma(self, obj):
        total_karma = obj.total_karma_user
        if total_karma:
            return total_karma.karma
        return None

    def get_rank(self, obj):
        roles = self.context.get('roles')
        user_karma = obj.total_karma_user.karma
        if RoleType.MENTOR.value in roles:
            ranks = TotalKarma.objects.filter(user__user_role_link_user__role__title=RoleType.MENTOR.value,
                                              karma__gte=user_karma).count()
        elif RoleType.ENABLER.value in roles:
            ranks = TotalKarma.objects.filter(user__user_role_link_user__role__title=RoleType.ENABLER.value,
                                              karma__gte=user_karma).count()
        else:
            ranks = TotalKarma.objects.filter(karma__gte=user_karma).exclude(
                Q(user__user_role_link_user__role__title__in=[RoleType.ENABLER.value, RoleType.MENTOR.value])).count()
        return ranks if ranks > 0 else None

    def get_karma_distribution(self, obj):
        karma_distribution = (
            KarmaActivityLog.objects
            .filter(created_by=obj)
            .values(task_type=F('task__type__title'))
            .annotate(karma=Sum('karma'))
            .order_by()
        )

        return karma_distribution

    def get_level(self, obj):
        user_level_link = obj.userlvllink_set.first()
        if user_level_link:
            return user_level_link.level.name
        return None

    # def get_interest_groups(self, obj):
    #
    #     interest_groups = (
    #         UserIgLink.objects.filter(user=obj).annotate(
    #             total_karma=Coalesce(
    #                 Sum('ig__tasklist__karmaactivitylog__karma',
    #                     filter=Q(ig__tasklist__karmaactivitylog__created_by=obj)), Value(0)
    #             )).values(name=F('ig__name'), karma=F('total_karma'))
    #     )
    #
    #     return interest_groups

    def get_interest_groups(self, obj):
        interest_groups = []
        for ig_link in UserIgLink.objects.filter(user=obj):
            total_ig_karma = 0 if KarmaActivityLog.objects.filter(task__ig=ig_link.ig, created_by=obj).aggregate(
                Sum('karma')).get(
                'karma__sum') is None else KarmaActivityLog.objects.filter(task__ig=ig_link.ig,
                                                                           created_by=obj).aggregate(
                Sum('karma')).get('karma__sum')
            interest_groups.append(
                {'name': ig_link.ig.name, 'karma': total_ig_karma})
        return interest_groups


class UserLevelsSerializer(ModelSerializer):
    level_number = serializers.CharField(source='level.level_order')
    task_names = serializers.SerializerMethodField()
    task_completed = serializers.SerializerMethodField()
    remaining_tasks = serializers.SerializerMethodField()

    class Meta:
        model = UserLvlLink
        fields = ["level_number", "task_names",
                  "task_completed", "remaining_tasks"]

    def get_task_names(self, obj):
        task_names = []
        for data in Level.objects.filter(id=obj.level_id):
            task_names.append(data.name)
            return task_names

    def get_task_completed(self, obj):
        return 1

    def get_remaining_tasks(self, obj):
        return 1

    def get_is_public(self, obj):
        user_settings = UserSettings.objects.filter(user=obj).first()
        if user_settings is not None:
            is_public_status = user_settings.is_public
        else:
            # Set a default value when UserSettings is not found
            is_public_status = False
        return is_public_status


class UserLevelSerializer(serializers.ModelSerializer):
    tasks = serializers.SerializerMethodField()

    class Meta:
        model = Level
        fields = ('name', 'tasks', 'karma')

    def get_tasks(self, obj):
        data = []
        for i in TaskList.objects.filter(level=obj, active=True):
            karma_activity = KarmaActivityLog.objects.filter(task=i, created_by=self.context.get('user_id'),
                                                             appraiser_approved=True)
            if karma_activity:
                completed = True
            else:
                completed = False

            data.append({'task_name': i.title, 'hashtag': i.hashtag,
                        'completed': completed, 'karma': i.karma})
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
        fields = ('first_name', 'last_name', 'role',
                  'rank', 'karma', 'interest_groups')

    def get_role(self, obj):
        roles = self.context.get('roles')
        if len(roles) == 0:
            return ['Learner']
        return roles

    def get_rank(self, obj):
        roles = self.context.get('roles')
        user_karma = obj.total_karma_user.karma
        if RoleType.MENTOR.value in roles:
            ranks = TotalKarma.objects.filter(user__user_role_link_user__role__title=RoleType.MENTOR.value,
                                              karma__gte=user_karma).count()
        elif RoleType.ENABLER.value in roles:
            ranks = TotalKarma.objects.filter(user__user_role_link_user__role__title=RoleType.ENABLER.value,
                                              karma__gte=user_karma).count()
        else:
            ranks = TotalKarma.objects.filter(karma__gte=user_karma).exclude(
                Q(user__user_role_link_user__role__title__in=[RoleType.ENABLER.value, RoleType.MENTOR.value])).count()
        return ranks if ranks > 0 else None

    def get_karma(self, obj):
        total_karma = obj.total_karma_user
        if total_karma:
            return total_karma.karma
        return None

    def get_interest_groups(self, obj):
        interest_groups = []
        for ig_link in UserIgLink.objects.filter(user=obj):
            interest_groups.append(ig_link.ig.name)
        return interest_groups


class ShareUserProfileUpdateSerializer(ModelSerializer):
    updated_by = serializers.CharField(required=False)
    updated_at = serializers.CharField(required=False)

    class Meta:
        model = UserSettings
        fields = ("is_public", "updated_by", "updated_at")

    def update(self, instance, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))
        instance.is_public = validated_data.get(
            'is_public', instance.is_public)
        instance.updated_by_id = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance
