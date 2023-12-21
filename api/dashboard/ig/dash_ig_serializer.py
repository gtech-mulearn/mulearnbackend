
from rest_framework import serializers

from db.task import InterestGroup


class InterestGroupSerializer(serializers.ModelSerializer):

    updated_by = serializers.CharField(source='updated_by.full_name')
    created_by = serializers.CharField(source='created_by.full_name')
    members = serializers.SerializerMethodField()

    class Meta:
        model = InterestGroup
        fields = [
            "id",
            "name",
            "icon",
            "code",
            "members",
            "updated_by",
            "updated_at",
            "created_by",
            "created_at",
        ]

    def get_members(self, obj):
        return obj.user_ig_link_ig.all().count()


class InterestGroupCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterestGroup
        fields = [
            "name",
            "code",
            "icon",
            "created_by",
            "updated_by"
        ]
