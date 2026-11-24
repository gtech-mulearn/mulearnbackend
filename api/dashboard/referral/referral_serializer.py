from rest_framework import serializers

from db.task import Wallet, UserLvlLink
from db.user import UserReferralLink


class ReferralListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="user.id")
    full_name = serializers.CharField(source="user.full_name")
    muid = serializers.CharField(source="user.muid")
    karma = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()

    class Meta:
        model = UserReferralLink
        fields = ["id", "full_name", "muid", "karma", "level"]

    # Wallet and UserLvlLink are one-to-one with User; ReferralListAPI
    # prefetches both (they were two queries per row, plus the level).
    def get_karma(self, obj):
        try:
            return obj.user.wallet_user.karma
        except Wallet.DoesNotExist:
            return 0

    def get_level(self, obj):
        try:
            return obj.user.user_lvl_link_user.level.name
        except UserLvlLink.DoesNotExist:
            return None
