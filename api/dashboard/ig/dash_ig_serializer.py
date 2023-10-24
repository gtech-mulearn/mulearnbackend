import uuid

from rest_framework import serializers

from db.task import InterestGroup
from db.user import User
from utils.utils import DateTimeUtils


class InterestGroupSerializer(serializers.ModelSerializer):

    updated_by = serializers.CharField(source='updated_by.fullname')
    created_by = serializers.CharField(source='created_by.fullname')
    user_ig_link_ig = serializers.SerializerMethodField()

    class Meta:
        model = InterestGroup
        fields = [
            "id",
            "name",
            "icon",
            "code",
            "user_ig_link_ig",
            "updated_by",
            "updated_at",
            "created_by",
            "created_at",
        ]

    def get_user_ig_link_ig(self, obj):
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
