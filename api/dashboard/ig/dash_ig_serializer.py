from rest_framework import serializers
import json

from db.task import InterestGroup
from db.user import User, Socials


def _resolve_muid_list(muid_list):
    """
    Given a list like [{"muid": "foo@mulearn"}, ...], fetch each user's
    details (including socials) from the DB and return an enriched list:
    [
        {
            "muid": "foo@mulearn",
            "full_name": "Foo Bar",
            "email": "foo@example.com",
            "profile_pic": "https://...",   # or null
            "socials": {
                "github": "...",
                "linkedin": "...",
                ...                          # null for unset fields
            }
        },
        ...
    ]
    MUIDs that don't match any User are included with null for extra fields.
    """
    if not isinstance(muid_list, list):
        return muid_list

    muids = [item.get("muid") for item in muid_list if isinstance(item, dict) and item.get("muid")]

    if not muids:
        return muid_list

    # Batch-fetch users
    user_objs = User.objects.filter(muid__in=muids)
    user_map = {u.muid: u for u in user_objs}

    # Batch-fetch socials keyed by user_id
    user_ids = [u.id for u in user_objs]
    socials_qs = Socials.objects.filter(user_id__in=user_ids).values(
        "user_id", "github", "facebook", "instagram", "linkedin",
        "dribble", "behance", "stackoverflow", "medium", "hackerrank"
    )
    socials_map = {s["user_id"]: s for s in socials_qs}

    enriched = []
    for item in muid_list:
        if not isinstance(item, dict):
            enriched.append(item)
            continue

        muid = item.get("muid")
        user = user_map.get(muid)

        if user:
            raw_socials = socials_map.get(user.id)
            socials = {
                "github":        raw_socials.get("github")        if raw_socials else None,
                "facebook":      raw_socials.get("facebook")      if raw_socials else None,
                "instagram":     raw_socials.get("instagram")     if raw_socials else None,
                "linkedin":      raw_socials.get("linkedin")      if raw_socials else None,
                "dribble":       raw_socials.get("dribble")       if raw_socials else None,
                "behance":       raw_socials.get("behance")       if raw_socials else None,
                "stackoverflow": raw_socials.get("stackoverflow") if raw_socials else None,
                "medium":        raw_socials.get("medium")        if raw_socials else None,
                "hackerrank":    raw_socials.get("hackerrank")    if raw_socials else None,
            }

            enriched.append({
                "muid":        muid,
                "full_name":   user.full_name,
                "email":       user.email,
                "profile_pic": user.profile_pic,
                "socials":     socials,
            })
        else:
            # muid not found — include as-is with null details
            enriched.append({
                "muid": muid,
                "full_name": None,
                "email": None,
                "profile_pic": None,
            })

    return enriched


class InterestGroupSerializer(serializers.ModelSerializer):

    updated_by = serializers.CharField(source="updated_by.full_name")
    created_by = serializers.CharField(source="created_by.full_name")
    members = serializers.SerializerMethodField()
    category = serializers.ChoiceField(
        choices=["maker", "coder", "creative", "manager", "others"]
    )
    status = serializers.ChoiceField(
        choices=["active", "requested", "cancelled", "rejected"]
    )

    class Meta:
        model = InterestGroup
        fields = [
            "id",
            "name",
            "resource",
            "about",
            "prerequisites",
            "career_opportunities",
            "top_blogs",
            "people_to_follow",
            "leads",
            "mentors",
            "thinktank",
            "office_hours",
            "icon",
            "code",
            "category",
            "status",
            "members",
            "updated_by",
            "updated_at",
            "created_by",
            "created_at",
        ]

    def get_members(self, obj):
        return obj.user_ig_link_ig.all().count()

    def to_representation(self, instance):
        """Convert JSON-serialized text fields back to Python objects for API output.
        For 'leads' and 'mentors', further enrich with user details from DB."""
        data = super().to_representation(instance)

        # Plain JSON fields — just parse the string back to Python
        plain_json_fields = [
            "prerequisites",
            "career_opportunities",
            "top_blogs",
            "people_to_follow",
        ]

        for field in plain_json_fields:
            val = data.get(field)
            if isinstance(val, str) and val:
                try:
                    data[field] = json.loads(val)
                except Exception:
                    pass  # leave as-is (plain string)

        # MUID fields — parse + enrich with user details
        for field in ["leads", "mentors"]:
            val = data.get(field)
            if isinstance(val, str) and val:
                try:
                    parsed = json.loads(val)
                    data[field] = _resolve_muid_list(parsed)
                except Exception:
                    pass  # leave as-is if parsing fails

        return data


class InterestGroupCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterestGroup
        fields = [
            "name",
            "code",
            "category",
            "status",
            "icon",
            "about",
            "prerequisites",
            "career_opportunities",
            "resource",
            "top_blogs",
            "people_to_follow",
            "leads",
            "mentors",
            "thinktank",
            "office_hours",
            "created_by",
            "updated_by",
        ]


class InterestGroupRequestSerializer(serializers.ModelSerializer):
    """Serializer for user-submitted IG creation requests."""

    class Meta:
        model = InterestGroup
        fields = [
            "name",
            "code",
            "category",
            "icon",
            "about",
            "prerequisites",
            "career_opportunities",
            "resource",
            "top_blogs",
            "people_to_follow",
            "leads",
            "mentors",
            "thinktank",
            "office_hours",
        ]
        extra_kwargs = {
            "name": {"required": True},
            "code": {"required": True},
            "category": {"required": True},
            "icon": {"required": True},
        }


class IGTopContributorSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    muid = serializers.CharField()
    karma_earned = serializers.IntegerField()


class IGTaskSummarySerializer(serializers.Serializer):
    ig_id = serializers.CharField()
    ig_name = serializers.CharField()
    ig_code = serializers.CharField()
    total_tasks_completed = serializers.IntegerField()
    total_karma_awarded = serializers.IntegerField()
    unique_contributors = serializers.IntegerField()
    top_contributors = IGTopContributorSerializer(many=True)
    date_range = serializers.DictField(
        child=serializers.DateField(allow_null=True), allow_null=True
    )
