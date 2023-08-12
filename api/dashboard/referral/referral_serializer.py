from rest_framework import serializers

from db.user import UserReferralLink


class ReferralListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='referral.id')
    full_name = serializers.CharField(source='referral.fullname')

    class Meta:
        model = UserReferralLink
        fields = ["id", "full_name"]
