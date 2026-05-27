from rest_framework import serializers

from db.company import CompanyUserLink


class CompanyMemberAddSerializer(serializers.Serializer):
    """Validates the payload for adding a user to a company roster."""
    user_id = serializers.UUIDField()
    role    = serializers.ChoiceField(choices=[r[0] for r in CompanyUserLink.ROLE_CHOICES])


class CompanyMemberSerializer(serializers.ModelSerializer):
    """Read-only serializer for a company member, including their muLearn profile."""
    user_id       = serializers.CharField(source="user.id", read_only=True)
    full_name     = serializers.CharField(source="user.full_name", read_only=True)
    muid          = serializers.CharField(source="user.muid", read_only=True)
    karma         = serializers.SerializerMethodField()
    level         = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()
    district      = serializers.SerializerMethodField()

    class Meta:
        model  = CompanyUserLink
        fields = [
            "id", "user_id", "full_name", "muid",
            "district", "karma", "level", "interest_groups",
            "role", "status", "created_at",
        ]
        read_only_fields = fields

    def get_karma(self, obj):
        wallet = getattr(obj.user, "wallet_user", None)
        return wallet.karma if wallet else 0

    def get_level(self, obj):
        lvl_link = getattr(obj.user, "user_lvl_link_user", None)
        if lvl_link is None:
            return None
        return {
            "id":          str(lvl_link.level.id),
            "name":        lvl_link.level.name,
            "level_order": lvl_link.level.level_order,
        }

    def get_interest_groups(self, obj):
        ig_links = obj.user.user_ig_link_user.all()
        return [{"id": str(link.ig.id), "name": link.ig.name} for link in ig_links]

    def get_district(self, obj):
        return obj.user.district.name if obj.user.district else None
