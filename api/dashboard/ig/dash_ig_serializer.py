from rest_framework import serializers

from db.task import InterestGroup


class InterestGroupSerializer(serializers.ModelSerializer):

    members = serializers.SerializerMethodField()
    category = serializers.ChoiceField(
        choices=["hardware", "coder", "creative", "manager", "others"]
    )
    logo = serializers.SerializerMethodField()

    def get_logo(self, obj):
        return (
            {
                "original": obj.logo.url,
                "thumbnail": obj.logo.thumbnail.url,
                "medium": obj.logo.medium.url,
            }
            if obj.logo
            else None
        )

    def get_members(self, obj):
        return obj.user_ig_link_ig.all().count()

    class Meta:
        model = InterestGroup
        fields = [
            "id",
            "name",
            "icon",
            "code",
            "category",
            "members",
            "short_description",
            "logo",
            "created_at",
        ]


class InterestGroupDetailSerializer(serializers.ModelSerializer):

    updated_by = serializers.CharField(source="updated_by.full_name")
    created_by = serializers.CharField(source="created_by.full_name")
    members = serializers.SerializerMethodField()
    category = serializers.ChoiceField(
        choices=["hardware", "coder", "creative", "manager", "others"]
    )
    logo = serializers.SerializerMethodField()

    def get_logo(self, obj):
        return (
            {
                "original": obj.logo.url,
                "thumbnail": obj.logo.thumbnail.url,
                "medium": obj.logo.medium.url,
            }
            if obj.logo
            else None
        )

    def get_members(self, obj):
        return obj.user_ig_link_ig.all().count()

    class Meta:
        model = InterestGroup
        fields = [
            "id",
            "name",
            "icon",
            "code",
            "category",
            "members",
            "short_description",
            "about",
            "logo",
            "cover_image",
            "updated_by",
            "updated_at",
            "created_by",
            "created_at",
        ]


class InterestGroupCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterestGroup
        fields = [
            "name",
            "code",
            "category",
            "icon",
            "logo",
            "cover_image",
            "about",
            "short_description",
            "created_by",
            "updated_by",
        ]
