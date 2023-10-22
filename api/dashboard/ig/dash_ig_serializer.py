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

    name = serializers.CharField(required=True)
    icon = serializers.CharField(required=True)
    code = serializers.CharField(required=True)

    class Meta:
        model = InterestGroup
        fields = [
            "name",
            "code",
            "icon"
        ]

    def create(self, validated_data):
        user_id = self.context.get('user_id')

        validated_data['id'] = str(uuid.uuid4())
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id

        return InterestGroup.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user_id = self.context.get('user_id')

        instance.name = validated_data.get('name', instance.name)
        instance.code = validated_data.get('code', instance.code)
        instance.icon = validated_data.get('icon', instance.icon)
        instance.updated_by_id = user_id
        instance.updated_by = DateTimeUtils.get_current_utc_time()

        instance.save()
        return instance

    def validate_name(self, name):
        ig_obj = InterestGroup.objects.filter(name=name).first()
        if ig_obj:
            raise serializers.ValidationError("interest group with name is already exists")
        if len(name) >= 75:
            raise serializers.ValidationError("name should contain only 75 characters")
        return name

    def validate_code(self, code):
        ig_obj = InterestGroup.objects.filter(code=code).first()
        if ig_obj:
            raise serializers.ValidationError("interest group with code is already exists")
        if len(code) >= 10:
            raise serializers.ValidationError("name should contain only 75 characters")
        return code

    def validate_icon(self, icon):
        if len(icon) >= 75:
            raise serializers.ValidationError("name should contain only 75 characters")
        return icon
