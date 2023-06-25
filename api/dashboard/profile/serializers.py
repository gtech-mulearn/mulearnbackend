from django.db.models import Sum, F, Q
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from db.task import KarmaActivityLog, TotalKarma, UserIgLink
from db.user import User, UserSettings
from utils.types import OrganizationType, RoleType


class UserLogSerializer(ModelSerializer):
    task_name = serializers.ReadOnlyField(source='task.title')
    karma_point = serializers.CharField(source='karma')
    created_date = serializers.CharField(source='created_at')

    class Meta:
        model = KarmaActivityLog
        fields = ["task_name", "karma_point", "created_date"]


class UserProfileSerializer(serializers.ModelSerializer):
    joined = serializers.DateTimeField(source="created_at")
    muid = serializers.CharField
    first_name = serializers.CharField
    last_name = serializers.CharField
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

    def get_is_public(self, obj):
        user_settings = UserSettings.objects.filter(user=obj).first()
        if user_settings is not None:
            is_public_status = user_settings.is_public
        else:
            # Set a default value when UserSettings is not found
            is_public_status = False
        return is_public_status
