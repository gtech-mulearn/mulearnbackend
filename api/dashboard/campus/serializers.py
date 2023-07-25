from django.db.models import Sum, F
from rest_framework import serializers

from db.organization import UserOrganizationLink
from db.task import UserLvlLink, TotalKarma, Level
from utils.types import OrganizationType


class UserOrgSerializer(serializers.ModelSerializer):
    fullname = serializers.ReadOnlyField(source="user.fullname")
    muid = serializers.ReadOnlyField(source="user.mu_id")
    karma = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()

    class Meta:
        model = TotalKarma
        fields = ("fullname", "karma", "muid", "rank", "level", 'created_at')

    def get_karma(self, obj):
        return obj.user.total_karma_user.karma or 0

    def get_rank(self, obj):
        rank = TotalKarma.objects.filter(
            user__total_karma_user__isnull=False
        ).annotate(
            rank=F('user__total_karma_user__karma')
        ).order_by('-rank').values_list('rank', flat=True)

        ranks = {karma: i + 1 for i, karma in enumerate(rank)}
        return ranks.get(obj.user.total_karma_user.karma, None)

    def get_level(self, obj):
        user_level_link = UserLvlLink.objects.filter(user=obj.user).first()
        if user_level_link:
            return user_level_link.level.name
        return None


class CollegeSerializer(serializers.ModelSerializer):
    college_name = serializers.ReadOnlyField(source="org.title")
    campus_code = serializers.ReadOnlyField(source="org.code")
    campus_zone = serializers.ReadOnlyField(source="org.district.zone.name")
    campus_lead = serializers.ReadOnlyField(source="user.fullname")
    total_karma = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()

    class Meta:
        model = UserOrganizationLink
        fields = ["college_name", "campus_lead", "campus_code",
                  "campus_zone", "total_karma", "total_members", "active_members", "rank"]

    def get_total_members(self, obj):
        return obj.org.user_organization_link_org_id.count()

    def get_active_members(self, obj):
        return obj.org.user_organization_link_org_id.filter(verified=True, user__active=True).count()

    def get_total_karma(self, obj):
        karma = obj.org.user_organization_link_org_id.filter(org__org_type=OrganizationType.COLLEGE.value,
                                                             verified=True,
                                                             user__total_karma_user__isnull=False).aggregate(
            total_karma=Sum('user__total_karma_user__karma'))
        return karma['total_karma'] or 0

    def get_rank(self, obj):
        rank = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value, verified=True, user__total_karma_user__isnull=False
        ).values('org').annotate(
            total_karma=Sum('user__total_karma_user__karma')
        ).order_by('-total_karma')

        college_ranks = {college['org']: i + 1 for i, college in enumerate(rank)}
        college_id = obj.org.id
        return college_ranks.get(college_id)


class StudentInEachLevelSerializer(serializers.ModelSerializer):
    level = serializers.ReadOnlyField(source='level_order')
    students = serializers.SerializerMethodField()

    class Meta:
        model = Level
        fields = ["level", "students"]

    def get_students(self, obj):
        user_org = self.context.get('user_org')
        user_level_link = UserLvlLink.objects.filter(level__level_order=obj.level_order,
                                                     user__user_organization_link_user_id__org__title=user_org).all()
        return len(user_level_link)
    


class WeeklyKarmaSerializer(serializers.ModelSerializer):
    college_name = serializers.ReadOnlyField(source="org.title")
    day_0 = serializers.SerializerMethodField()
    day_1 = serializers.SerializerMethodField()
    day_2 = serializers.SerializerMethodField()
    day_3 = serializers.SerializerMethodField()
    day_4 = serializers.SerializerMethodField()
    day_5 = serializers.SerializerMethodField()
    day_6 = serializers.SerializerMethodField()

    days = 7
    

    class Meta:
        model = UserOrganizationLink
        fields = ["college_name", "day_0", "day_1", "day_2", "day_3", "day_4", "day_5", "day_6"]

    def karma_by_date(self, obj, days_delta):
        today = DateTimeUtils.get_current_utc_time().date()
        date = today - timedelta(days=days_delta)
        students = UserOrganizationLink.objects.filter(org_id=obj.org_id)
        karma = 0
        for student in students:
            karma_logs = KarmaActivityLog.objects.filter(user=student.user, created_at__date=date).aggregate(
                total_karma=Sum('karma'))
            karma += karma_logs['total_karma'] or 0
        return karma

    def get_day_0(self, obj):
        return self.karma_by_date(obj, 0)
    
    def get_day_1(self, obj):
        return self.karma_by_date(obj, 1)
    
    def get_day_2(self, obj):
        return self.karma_by_date(obj, 2)
    
    def get_day_3(self, obj):
        return self.karma_by_date(obj, 3)
    
    def get_day_4(self, obj):
        return self.karma_by_date(obj, 4)
    
    def get_day_5(self, obj):
        return self.karma_by_date(obj, 5)
    
    def get_day_6(self, obj):
        return self.karma_by_date(obj, 6)
    

