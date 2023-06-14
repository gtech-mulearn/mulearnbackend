from rest_framework import serializers
from db.organization import Organization
from db.user import User
from db.task import TotalKarma


class ZonalStudents(serializers.ModelSerializer):
    karma = serializers.IntegerField()
    rank = serializers.SerializerMethodField()

    def get_rank(self, obj):
        queryset = self.context["queryset"]
        sorted_persons = sorted(
            queryset,
            key=lambda x: x.karma,
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



class ZonalCampus(serializers.ModelSerializer):
    total_karma = serializers.IntegerField()
    total_members = serializers.IntegerField()
    active_members = serializers.IntegerField()
    rank = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "title",
            "code",
            "org_type",
            "total_karma",
            "total_members",
            "active_members",
            "rank"
        ]

    def get_rank(self, obj):
        queryset = self.context["queryset"]
        
        sorted_campuses = sorted(
            queryset,
            key=lambda campus: campus.total_karma,
            reverse=True,
        )
        for i, campus in enumerate(sorted_campuses):
            if campus == obj:
                return i + 1
