from rest_framework import serializers

from db.user import User


class LearnerIGSerializer(serializers.Serializer):
    """Serializes a single Interest Group entry for a learner."""
    id = serializers.CharField()
    name = serializers.CharField()


class LearnerLevelSerializer(serializers.Serializer):
    """Serializes a learner's current level."""
    id = serializers.CharField()
    name = serializers.CharField()
    level_order = serializers.IntegerField()


class LearnerListSerializer(serializers.ModelSerializer):
    """
    Flattens User + Wallet + Level + IG memberships into a single object.
    All relational data is expected to be pre-fetched / pre-annotated on the
    queryset to avoid N+1 queries.
    """
    karma = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "muid",
            "full_name",
            "gender",
            "district",
            "karma",
            "level",
            "interest_groups",
            "interested_in_work",
            "interested_in_gig_work",
        ]

    # ------------------------------------------------------------------ #
    # Field resolvers                                                       #
    # ------------------------------------------------------------------ #

    def get_karma(self, obj):
        """
        Reads from the pre-fetched `wallet_user` reverse OneToOne relation.
        Returns 0 if the wallet does not exist.
        """
        wallet = getattr(obj, "wallet_user", None)
        if wallet is None:
            return 0
        return wallet.karma

    def get_level(self, obj):
        """
        Reads from the pre-fetched `user_lvl_link_user` reverse OneToOne.
        Returns None if the learner has no level assigned.
        """
        lvl_link = getattr(obj, "user_lvl_link_user", None)
        if lvl_link is None:
            return None
        level = lvl_link.level
        return LearnerLevelSerializer(level).data

    def get_interest_groups(self, obj):
        """
        Reads from the pre-fetched `user_ig_link_user` reverse FK.
        Returns a list of {id, name} dicts.
        """
        ig_links = obj.user_ig_link_user.all()
        return [{"id": str(link.ig.id), "name": link.ig.name} for link in ig_links]

    def get_district(self, obj):
        """Returns the district name or None."""
        return obj.district.name if obj.district else None
