from django.conf import settings
from rest_framework import serializers

from db.task import InterestGroup


class InterestGroupSerializer(serializers.ModelSerializer):

    updated_by = serializers.CharField(source="updated_by.full_name")
    created_by = serializers.CharField(source="created_by.full_name")
    members = serializers.SerializerMethodField()
    banner_image = serializers.SerializerMethodField()
    category = serializers.ChoiceField(
        choices=["maker", "coder", "creative", "manager", "others"]
    )

    class Meta:
        model = InterestGroup
        fields = [
            "id",
            "name",
            "icon",
            "code",
            "category",
            "banner_image",
            "members",
            "updated_by",
            "updated_at",
            "created_by",
            "created_at",
        ]

    def get_banner_image(self, obj):
        return f"{settings.MEDIA_URL}{media}" if (media := obj.banner_image) else None

    def get_members(self, obj):
        return obj.user_ig_link_ig.all().count()


class InterestGroupCreateUpdateSerializer(serializers.ModelSerializer):
    banner_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = InterestGroup
        fields = [
            "name",
            "code",
            "category",
            "icon",
            "banner_image",
            "created_by",
            "updated_by",
        ]

    def update(self, instance, validated_data):
        if "banner_image" in validated_data:
            new_banner = validated_data.get("banner_image")
            if instance.banner_image and instance.banner_image != new_banner:
                instance.banner_image.delete(save=False)
        return super().update(instance, validated_data)

