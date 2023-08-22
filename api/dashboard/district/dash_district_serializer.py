from datetime import timedelta

from django.db.models import Sum, F
from rest_framework import serializers

from db.organization import UserOrganizationLink, Organization, College
from db.task import TotalKarma, KarmaActivityLog, UserLvlLink, Level
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils


# class DistrictStudents(serializers.ModelSerializer):
#     karma = serializers.SerializerMethodField()
#     rank = serializers.SerializerMethodField()
#
#     def get_karma(self, obj):
#         try:
#             return obj.total_karma_user.karma
#         except TotalKarma.DoesNotExist:
#             return 0
#
#     def get_rank(self, obj):
#         queryset = self.context["queryset"]
#         sorted_persons = sorted(
#             (person for person in queryset if hasattr(person, "total_karma_user")),
#             key=lambda x: x.total_karma_user.karma,
#             reverse=True,
#         )
#         for i, person in enumerate(sorted_persons):
#             if person == obj:
#                 return i + 1
#
#     class Meta:
#         model = User
#         fields = [
#             "first_name",
#             "last_name",
#             "email",
#             "mobile",
#             "mu_id",
#             "karma",
#             "rank",
#         ]
#
#
# class DistrictCampus(serializers.ModelSerializer):
#     total_karma = serializers.IntegerField()
#     total_members = serializers.IntegerField()
#     active_members = serializers.IntegerField()
#     rank = serializers.SerializerMethodField()
#
#     class Meta:
#         model = Organization
#         fields = [
#             "id",
#             "title",
#             "code",
#             "org_type",
#             "total_karma",
#             "total_members",
#             "active_members",
#             "rank"
#         ]
#
#     def get_rank(self, obj):
#         queryset = self.context["queryset"]
#
#         sorted_campuses = sorted(
#             queryset,
#             key=lambda campus: campus.total_karma,
#             reverse=True,
#         )
#         for i, campus in enumerate(sorted_campuses):
#             if campus == obj:
#                 return i + 1


class DistrictDetailsSerializer(serializers.ModelSerializer):
    district = serializers.CharField(source="org.district.name")
    zone = serializers.CharField(source="org.district.zone.name")
    rank = serializers.SerializerMethodField()
    district_lead = serializers.SerializerMethodField()
    karma = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()

    class Meta:
        model = UserOrganizationLink
        fields = ("district", "zone", "rank", "district_lead", "karma", "total_members", "active_members")

    def get_rank(self, obj):
        user_org_link = UserOrganizationLink.objects.filter(org__org_type=OrganizationType.COLLEGE.value).values(
            'org', 'org__district__name').annotate(total_karma=Sum('user__total_karma_user__karma')
                                                   ).order_by('-total_karma')
        rank_dict = {}
        for data in user_org_link:
            district_name = data['org__district__name']
            total_karma = data['total_karma']

            if district_name in rank_dict:
                rank_dict[district_name] += total_karma
            else:
                rank_dict[district_name] = total_karma

        sorted_rank_dict = dict(sorted(rank_dict.items(), key=lambda x: x[1], reverse=True))

        if obj.org.district.name in sorted_rank_dict:
            keys_list = list(sorted_rank_dict.keys())
            position = keys_list.index(obj.org.district.name)
            return position + 1

    def get_district_lead(self, obj):
        user_org_link = UserOrganizationLink.objects. \
            filter(org__district__name=obj.org.district.name,
                   user__user_role_link_user__role__title='District Campus Lead').first()
        return user_org_link.user.fullname if user_org_link else None

    def get_karma(self, obj):
        user_org_link = UserOrganizationLink.objects.filter(org__district__name=obj.org.district.name).aggregate(
            total_karma=Sum('user__total_karma_user__karma'))['total_karma']
        return user_org_link

    def get_total_members(self, obj):
        user_org_link = UserOrganizationLink.objects.filter(org__district__name=obj.org.district.name).all()
        return len(user_org_link)

    def get_active_members(self, obj):
        today = DateTimeUtils.get_current_utc_time()
        start_date = today.replace(day=1)
        end_date = start_date.replace(day=1, month=start_date.month % 12 + 1) - timedelta(days=1)

        user_org_link = UserOrganizationLink.objects.filter(org__district__name=obj.org.district.name).all()
        active_members = []
        for data in user_org_link:
            karma_activity_log = KarmaActivityLog.objects.filter(user=data.user, created_at__range=(
                start_date, end_date)).first()
            if karma_activity_log is not None:
                active_members.append(karma_activity_log)
        return len(active_members)


class DistrictTopThreeCampusSerializer(serializers.ModelSerializer):
    rank = serializers.SerializerMethodField()
    campus_code = serializers.CharField(source='code')

    class Meta:
        model = Organization
        fields = ["rank", "campus_code"]

    def get_rank(self, obj):
        rank = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value, org__district__name=obj.district.name, verified=True,
            user__total_karma_user__isnull=False).values('org').annotate(
            total_karma=Sum('user__total_karma_user__karma')).order_by('-total_karma')
        college_ranks = {college['org']: i + 1 for i, college in enumerate(rank)}
        college_id = obj.id
        return college_ranks.get(college_id)


class DistrictStudentLevelStatusSerializer(serializers.ModelSerializer):
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
                user=obj.user_organization_link_org_id))
            level_list.append(level_dict)
            level_dict = {}
        return level_list


# {
#     "hasError": false,
#     "statusCode": 200,
#     "message": {
#         "general": []
#     },
#     "response": [
#         {
#             "college_name": "SREENARAYAGURU COLLEGE OF ARTS AND SCIENCE",
#             "college_code": "SNTCSS",
#             "level": [
#                 {
#                     "level": 5,
#                     "students_count": 0
#                 },
#                 {
#                     "level": 3,
#                     "students_count": 0
#                 },
#                 {
#                     "level": 1,
#                     "students_count": 0
#                 }
#             ]
#         },
#         {
#             "college_name": "CO-OPERATIVE ARTS & SCIENCE COLLEGE,MADAI, PAZHAYANGADI",
#             "college_code": "CAS",
#             "level": [
#                 {
#                     "level": 5,
#                     "students_count": 0
#                 },
#                 {
#                     "level": 3,
#                     "students_count": 0
#                 },
#                 {
#                     "level": 1,
#                     "students_count": 0
#                 }
#             ]
#         },

class DistrictStudentDetailsSerializer(serializers.ModelSerializer):
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
        fields = ('title', 'code', 'lead', 'lead_number')

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
