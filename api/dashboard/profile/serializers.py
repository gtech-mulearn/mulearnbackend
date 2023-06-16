from django.db.models import Sum, F, Value, Q
from django.db.models.functions import Coalesce
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from db.task import KarmaActivityLog, TotalKarma, UserIgLink
from db.user import User
from utils.types import OrganizationType


class UserLogSerializer(ModelSerializer):
    taskName = serializers.ReadOnlyField(source='task.title')
    karmaPoint = serializers.CharField(source='karma')
    createdDate = serializers.CharField(source='created_at')

    class Meta:
        model = KarmaActivityLog
        fields = ["taskName", "karmaPoint", "createdDate"]


class UserProfileSerializer(serializers.ModelSerializer):
    joined = serializers.DateTimeField(source="created_at")
    muid = serializers.CharField(source="mu_id")
    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")
    roles = serializers.SerializerMethodField()
    college_code = serializers.SerializerMethodField()
    karma = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    karma_distribution = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'joined', 'firstName', 'lastName', 'gender', 'muid', 'roles', 'college_code', 'karma', 'rank',
            'karma_distribution', 'level', 'profile_pic', 'interest_groups'
        )

    def get_roles(self, obj):
        return list(obj.user_role_link_user.values_list('role__title', flat=True))

    def get_college_code(self, obj):
        user_org_link = obj.user_organization_link_user_id.filter(org__org_type=OrganizationType.COLLEGE.value).first()
        if user_org_link:
            return user_org_link.org.code
        return None

    def get_karma(self, obj):
        total_karma = obj.total_karma_user
        if total_karma:
            return total_karma.karma
        return None

    def get_rank(self, obj):
        user_karma = obj.total_karma_user.karma
        ranks = TotalKarma.objects.filter(karma__gte=user_karma).count()
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

    def get_interest_groups(self, obj):
        interest_groups = (
            UserIgLink.objects
            .filter(user=obj)
            .annotate(
                total_karma=Coalesce(
                    Sum(
                        'ig__tasklist__karmaactivitylog__karma',
                        filter=Q(ig__tasklist__karmaactivitylog__created_by=obj)
                    ),
                    Value(0)
                )
            )
            .values(name=F('ig__name'), karma=F('total_karma'))
        )
        return interest_groups
