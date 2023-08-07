from rest_framework import serializers
from db.task import InterestGroup
from db.user import User
import uuid
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
        return len(obj.user_ig_link_ig.all())


class InterestGroupCreateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True, error_messages={
        'required': 'code field must not be left blank.'
    })
    icon = serializers.CharField(required=True, error_messages={
        'required': 'icon field must not be left blank.'
    })

    class Meta:
        model = InterestGroup
        fields = [
            "name",
            "code",
            "icon"
        ]

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        return InterestGroup.objects.create(
            id=uuid.uuid4(),
            name=validated_data.get('name'),
            code=validated_data.get('code'),
            icon=validated_data.get('icon'),
            updated_by_id=user_id,
            updated_at=DateTimeUtils.get_current_utc_time(),
            created_by_id=user_id,
            created_at=DateTimeUtils.get_current_utc_time(),
        )


class InterestGroupUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterestGroup
        fields = [
            "name",
            "code",
            "icon"
        ]

    def update(self, instance, validated_data):
        user_id = self.context.get('user_id')
        user = User.objects.filter(id=user_id).first()
        instance.name = validated_data.get('name')
        instance.code = validated_data.get('code')
        instance.icon = validated_data.get('icon')
        instance.updated_by = user
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance
