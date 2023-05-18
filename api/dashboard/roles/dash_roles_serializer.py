from rest_framework import serializers
from db.user import Role

class RoleDashboardSerializer(serializers.ModelSerializer):

    class Meta:
        model = Role
        fields = "__all__"
        