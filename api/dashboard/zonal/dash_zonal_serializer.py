from datetime import timedelta

from django.db.models import Sum, F
from rest_framework import serializers

from db.organization import UserOrganizationLink, District, Organization, College
from db.task import KarmaActivityLog, Level, UserLvlLink, TotalKarma
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils


class ZonalDetailsSerializer(serializers.ModelSerializer):
    zone = serializers.CharField(source="org.district.zone.name")
    rank = serializers.SerializerMethodField()
    zonal_lead = serializers.SerializerMethodField()
    karma = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()

    class Meta:
        model = UserOrganizationLink
        fields = ["zone", "rank", "zonal_lead", "karma", "total_members", "active_members"]

    def get_rank(self, obj):

        user_org_link = UserOrganizationLink.objects.filter(org__org_type=OrganizationType.COLLEGE.value).values(
            'org', 'org__district__zone__name').annotate(total_karma=Sum('user__total_karma_user__karma'
                                                                         )).order_by('-total_karma')
        rank_dict = {}
        for data in user_org_link:
            zone_name = data['org__district__zone__name']
            total_karma = data['total_karma']

            if zone_name in rank_dict:
                rank_dict[zone_name] += total_karma
            else:
                rank_dict[zone_name] = total_karma

        sorted_rank_dict = dict(sorted(rank_dict.items(), key=lambda x: x[1], reverse=True))

        if obj.org.district.zone.name in sorted_rank_dict:
            keys_list = list(sorted_rank_dict.keys())
            position = keys_list.index(obj.org.district.zone.name)
            return position + 1

    def get_zonal_lead(self, obj):
        user_org_link = UserOrganizationLink.objects. \
            filter(org__district__zone__name=obj.org.district.zone.name,
                   user__user_role_link_user__role__title=RoleType.ZONAL_CAMPUS_LEAD.value).first()
        return user_org_link.user.fullname if user_org_link else None

    def get_karma(self, obj):
        user_org_link = UserOrganizationLink.objects.filter(
            org__district__zone__name=obj.org.district.zone.name).aggregate(
            total_karma=Sum('user__total_karma_user__karma'))['total_karma']
        return user_org_link

    def get_total_members(self, obj):
        user_org_link = UserOrganizationLink.objects.filter(org__district__zone__name=obj.org.district.zone.name).all()
        return len(user_org_link)

    def get_active_members(self, obj):
        today = DateTimeUtils.get_current_utc_time()
        start_date = today.replace(day=1)
        end_date = start_date.replace(day=1, month=start_date.month % 12 + 1) - timedelta(days=1)
        user_org_link = UserOrganizationLink.objects.filter(org__district__zone__name=obj.org.district.zone.name).all()
        active_members = []
        for data in user_org_link:
            karma_activity_log = KarmaActivityLog.objects.filter(user=data.user, created_at__range=(
                start_date, end_date)).first()
            if karma_activity_log is not None:
                active_members.append(karma_activity_log)
        return len(active_members)


class ZonalTopThreeDistrictSerializer(serializers.ModelSerializer):
    rank = serializers.SerializerMethodField()
    district = serializers.CharField(source='name')

    class Meta:
        model = District
        fields = ["rank", "district"]

    def get_rank(self, obj):
        rank = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value,
            org__district__zone__name=obj.zone.name, verified=True).values('org__district').annotate(
            total_karma=Sum('user__total_karma_user__karma')).order_by('-total_karma')
        district_ranks = {district['org__district']: i + 1 for i, district in enumerate(rank)}
        district_id = obj.id
        return district_ranks.get(district_id)


class ZonalStudentLevelStatusSerializer(serializers.ModelSerializer):
    college_name = serializers.CharField(source='title')
    college_code = serializers.CharField(source='code')
    level = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["college_name", "college_code", "level"]

    def get_level(self, obj):
        level = Level.objects.all()
        level_dict = {}
        level_list = []
        for levels in level:
            level_dict['level'] = levels.level_order
            level_dict['students_count'] = len(UserLvlLink.objects.filter(
                level=levels,
                user__user_organization_link_user_id=obj.user_organization_link_org_id).all())
            level_list.append(level_dict)
            level_dict = {}
        return level_list


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


class ZonalStudentDetailsSerializer(serializers.ModelSerializer):
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


class ListAllDistrictsSerializer(serializers.ModelSerializer):
    level = serializers.SerializerMethodField()
    lead = serializers.SerializerMethodField()
    lead_number = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ('title', 'code', 'level', 'lead', 'lead_number')

    def get_level(self, obj):
        college = College.objects.filter(org=obj).first()
        return college.level if college else None

    def get_lead(self, obj):
        user_org_link = obj.user_organization_link_org_id.filter(
            org__title=obj.title,
            user__user_role_link_user__role__title=RoleType.CAMPUS_LEAD.value).first()
        return user_org_link.user.fullname if user_org_link else None

    def get_lead_number(self, obj):
        user_org_link = obj.user_organization_link_org_id.filter(
            org__title=obj.title,
            user__user_role_link_user__role__title=RoleType.CAMPUS_LEAD.value).first()
        return user_org_link.user.mobile if user_org_link else None