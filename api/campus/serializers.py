from rest_framework import serializers
from db.organization import UserOrganizationLink
from db.task import TotalKarma


class UserOrgSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source="user.fullname")
    email = serializers.ReadOnlyField(source="user.email")
    phone = serializers.ReadOnlyField(source="user.mobile")
    # totalKarma = serializers.SerializerMethodField()
    class Meta:
        model = TotalKarma
        fields = ["name","email","phone","karma"]

        