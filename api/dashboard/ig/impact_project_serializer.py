from rest_framework import serializers

from db.impact_project import ImpactProject, ImpactProjectLink, ImpactProjectUserLink


class ImpactProjectTeamMemberSerializer(serializers.ModelSerializer):
    muid = serializers.CharField(source="user.muid")
    name = serializers.CharField(source="user.full_name")
    avatar = serializers.CharField(source="user.profile_pic", read_only=True, allow_null=True)

    class Meta:
        model = ImpactProjectUserLink
        fields = ["muid", "name", "avatar", "is_lead"]


class ImpactProjectLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImpactProjectLink
        fields = ["label", "url"]


class ImpactProjectSerializer(serializers.ModelSerializer):
    ig_id = serializers.CharField(source="ig.id", read_only=True)
    team = serializers.SerializerMethodField()
    links = serializers.SerializerMethodField()
    image = serializers.CharField(read_only=True)
    created_by = serializers.CharField(source="created_by.full_name", read_only=True)
    updated_by = serializers.CharField(source="updated_by.full_name", read_only=True)

    class Meta:
        model = ImpactProject
        fields = [
            "id", "ig_id", "title", "image", "description", "team", "links",
            "created_by", "updated_by", "created_at", "updated_at",
        ]

    def get_team(self, obj):
        if hasattr(obj, "_prefetched_objects_cache") and "impact_project_user_link_project" in obj._prefetched_objects_cache:
            links = obj.impact_project_user_link_project.all()
        else:
            links = obj.impact_project_user_link_project.select_related("user").all()
        return ImpactProjectTeamMemberSerializer(links, many=True).data

    def get_links(self, obj):
        links = obj.impact_project_link_project.all()
        return ImpactProjectLinkSerializer(links, many=True).data


class ImpactProjectCreateUpdateSerializer(serializers.ModelSerializer):
    # Declared so the repo-wide strict-serializer patch (mulearnbackend/__init__.py,
    # which rejects any request key not in self.fields) doesn't 400 on these — they
    # are not model fields, actual persistence is handled by the view via
    # request_data["team"]/["links"], not validated_data.
    team = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)
    links = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)

    class Meta:
        model = ImpactProject
        fields = ["ig", "title", "description", "created_by", "updated_by", "team", "links"]

    def validate(self, attrs):
        attrs.pop("team", None)
        attrs.pop("links", None)
        # A project may now have zero, one, or multiple leads — no count restriction.
        # Actual muid resolution (including rejecting entries missing a muid) is
        # enforced in the view via _resolve_team, since it needs a DB lookup.
        return attrs
