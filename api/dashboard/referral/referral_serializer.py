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

    def get_karma(self, obj):
        total_karma = Wallet.objects.filter(user=obj.user).first()
        return total_karma.karma if total_karma else 0

    def get_level(self, obj):
        user_level_link = UserLvlLink.objects.filter(user=obj.user).first()
        return user_level_link.level.name if user_level_link else None
