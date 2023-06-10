from django.db.models import Count, F
from django.db.models import Sum
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from db.organization import UserOrganizationLink
from db.task import KarmaActivityLog, TotalKarma, UserIgLink, UserLvlLink
from db.user import User
from utils.types import OrganizationType


class UserLogSerializer(ModelSerializer):
    taskName = serializers.ReadOnlyField(source='task.title')
    karmaPoint = serializers.CharField(source='karma')
    createdDate = serializers.CharField(source='created_at')

    class Meta:
        model = KarmaActivityLog
        fields = ["taskName", "karmaPoint", "createdDate"]


class UserInterestGroupSerializer(ModelSerializer):
    interestGroup = serializers.ReadOnlyField(source='ig.name')

    class Meta:
        model = UserIgLink
        fields = ["interestGroup"]


class UserSuggestionSerializer(ModelSerializer):
    totalKarma = serializers.IntegerField(source="karma")
    fullName = serializers.ReadOnlyField(source="user.fullname")

    class Meta:
        model = TotalKarma
        fields = ["fullName", "totalKarma"]


class UserProfileSerializer(serializers.ModelSerializer):
    joined = serializers.CharField(source="created_at")
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
            'id', 'joined', 'firstName', 'lastName','gender', 'muid', 'roles', 'college_code', 'karma', 'rank',
            'karma_distribution', 'level', 'interest_groups',)

    def get_roles(self, obj):
        return [
            user_role_link.role.title
            for user_role_link in obj.user_role_link_user.all()
        ]

    def get_college_code(self, obj):
        user_org_link = UserOrganizationLink.objects.filter(user=obj,
                                                            org__org_type=OrganizationType.COLLEGE.value).first()
        if user_org_link:
            return user_org_link.org.code
        return None

    def get_karma(self, obj):
        total_karma = TotalKarma.objects.filter(user=obj).first()
        if total_karma:
            return total_karma.karma
        return None

    def get_rank(self, obj):
        total_karma = TotalKarma.objects.all().order_by('-karma')
        rank = 1
        for karma in total_karma:
            if karma.user == obj:
                return rank
            rank += 1
        return None

    def get_karma_distribution(self, obj):
        karma_distribution = (
            KarmaActivityLog.objects
            .filter(created_by=obj)
            .values(task_type=F('task__type__title'))
            .annotate(karma=Count('karma'))
        )

        return karma_distribution

    def get_level(self, obj):
        user_level_link = UserLvlLink.objects.filter(user=obj).first()
        if user_level_link:
            return user_level_link.level.name
        return None

    def get_interest_groups(self, obj):
        interest_groups = []
        for ig_link in UserIgLink.objects.filter(user=obj):
            total_ig_karma = 0 if KarmaActivityLog.objects.filter(task__ig=ig_link.ig, created_by=obj).aggregate(
                Sum('karma')).get(
                'karma__sum') is None else KarmaActivityLog.objects.filter(task__ig=ig_link.ig,
                                                                           created_by=obj).aggregate(
                Sum('karma')).get('karma__sum')
            interest_groups.append({'name': ig_link.ig.name, 'karma': total_ig_karma})

        return interest_groups
