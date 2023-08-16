from rest_framework import serializers

from db.task import TotalKarma
from db.task import UserLvlLink
from db.user import UserReferralLink


class ReferralListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='referral.id')
    full_name = serializers.CharField(source='referral.fullname')
    muid = serializers.CharField(source='referral.mu_id')
    karma = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()

    class Meta:
        model = UserReferralLink
        fields = ["id", "full_name", "muid", "karma", "level"]

    def get_karma(self, obj):
        total_karma = TotalKarma.objects.filter(user_id=obj.referral).first()
        return total_karma.karma if total_karma else 0

    def get_level(self, obj):
        user_level_link = UserLvlLink.objects.filter(user_id=obj.referral).first()
        return user_level_link.level.name if user_level_link else None
