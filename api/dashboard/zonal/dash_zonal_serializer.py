from rest_framework import serializers
from db.organization import Organization
from db.user import User
from db.task import TotalKarma
from django.db.models import Sum


class ZonalStudents(serializers.ModelSerializer):
    karma = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()

    def get_karma(self, obj):
        try:
            return obj.total_karma_user.karma
        except TotalKarma.DoesNotExist:
            return 0

    def get_rank(self, obj):
        queryset = self.context["queryset"]
        sorted_persons = sorted(
            (person for person in queryset if hasattr(person, "total_karma_user")),
            key=lambda x: x.total_karma_user.karma,
            reverse=True,
        )
        for i, person in enumerate(sorted_persons):
            if person.id == obj.id:
                return i + 1

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "mobile",
            "mu_id",
            "karma",
            "rank",
        ]


class ZonalCampus(serializers.ModelSerializer):
    total_karma = serializers.SerializerMethodField()
    district_name = serializers.ReadOnlyField(source="district.name")
    # zone_name = serializers.ReadOnlyField(source="district.zone.name")
    total_members = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()
    # rank = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "title",
            "code",
            "org_type",
            "total_karma",
            "district_name",
            "total_members",
            "active_members",
            # "zone_name",
            # "rank",
        ]

    def get_total_members(self, obj):
        return obj.user_organization_link_org_id.count()

    def get_active_members(self, obj):
        return obj.user_organization_link_org_id.filter(
            verified=True, user__active=True
        ).count()

    def get_total_karma(self, obj):
        total_karma = obj.user_organization_link_org_id.filter(verified=True).aggregate(
            total_karma=Sum("user__total_karma_user__karma")
        )["total_karma"]
        return total_karma or 0


    # def get_rank(self, obj):
    #     queryset = self.context["queryset"]
    #     rank = queryset.filter(total_karma__gt=obj.total_karma).count() + 1
    #     return rank if obj.total_karma else None

    # def get_rank(self, obj):
    #     orgs = Organization.objects.filter(org_type="College")

    #     results = []
    #     for org in orgs:
    #         for user_org_link in org.user_organization_link_org_id.filter(
    #             verified=True
    #         ):
    #             results.append(user_org_link.user.total_karma_user.karma)

    #     results.sort(reverse=True)

    #     colleges = {}
    #     for i, karma in enumerate(results):
    #         colleges[karma] = i + 1

    #     rank = colleges.get(obj.user.total_karma_user.karma, None)

    #     return rank


# def get_rank(self, obj):
#     orgs = Organization.objects.filter(org_type="College")
#     results = []
#
#     for org in orgs:
#         for user_org_link in org.user_organization_link_org_id.filter(verified=True):
#             results.append({'rank': 0, 'college': org.title, 'totalKarma': user_org_link.user.total_karma_user.karma})
#     results.sort(key=lambda x: x['totalKarma'], reverse=True)
#     colleges = {}
#     for i, college in enumerate(results):
#         colleges[college.get('college')] = i+1
#     return colleges[obj.org.title]
