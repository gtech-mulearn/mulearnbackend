from rest_framework import serializers

from db.campus import CampusExecom


class CampusExecomMemberSerializer(serializers.ModelSerializer):
    uid = serializers.CharField(source="user.id")
    muid = serializers.CharField(source="user.muid")
    full_name = serializers.CharField(source="user.full_name")
    role_title = serializers.CharField(source="role.title")
    profile_pic = serializers.SerializerMethodField()

    class Meta:
        model = CampusExecom
        fields = [
            "id",
            "uid",
            "muid",
            "full_name",
            "profile_pic",
            "role_title",
            "created_at",
            "updated_at",
        ]

    def get_profile_pic(self, obj):
        return str(obj.user.profile_pic) if obj.user.profile_pic else None


class CampusExecomAssignSerializer(serializers.Serializer):
    uid = serializers.CharField()
    role_title = serializers.CharField(required=False)
    role = serializers.CharField(required=False)

    def validate(self, attrs):
        role_title = attrs.get("role_title") or attrs.get("role")
        if not role_title:
            raise serializers.ValidationError(
                {"role_title": ["role_title (or role) is required"]}
            )

        attrs["role_title"] = role_title.strip()
        if not attrs["role_title"]:
            raise serializers.ValidationError({"role_title": ["This field may not be blank."]})

        return attrs
