from rest_framework import serializers
from db.organization import Organization
from db.user import User
from db.task import TotalKarma
from django.db.models import Sum


class DistrictStudents(serializers.ModelSerializer):
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
            if person == obj:
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


class DistrictCampus(serializers.ModelSerializer):
    total_karma = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "title",
            "code",
            "org_type",
            "total_karma",
            "total_members",
            "active_members",
            "rank"
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

    def get_rank(self, obj):
        queryset = self.context["queryset"]
        
        sorted_campuses = sorted(
            queryset,
            key=self.get_total_karma,
            reverse=True,
        )
        for i, campus in enumerate(sorted_campuses):
            if campus == obj:
                return i + 1