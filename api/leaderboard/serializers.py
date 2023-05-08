from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from db.task import TotalKarma


class StudentLeaderboardSerializer(ModelSerializer):
    totalKarma = serializers.IntegerField(source="karma")
    name = serializers.ReadOnlyField(source="user.fullname")
    institution = serializers.SerializerMethodField()

    class Meta:
        model = TotalKarma
        fields = ["name", "totalKarma", "institution"]

    def get_institution(self, obj):
        try:
            user_organization = obj.user.user_organization_link_user_id.first()
            return user_organization.org.code if user_organization.org else None
        except:
            return None
