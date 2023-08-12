from rest_framework import serializers

from db.user import UserReferralLink


class ReferralListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name')

    class Meta:
        model = UserReferralLink
        fields = ["id", "full_name"]
