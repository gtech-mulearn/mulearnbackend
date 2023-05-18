from rest_framework import serializers
from db.user import User


                # "id",
                # "title",
                # "description",
                # "updated_by",
                # "updated_at",
                # "created_by",
                # "verified",
                # "created_at",

class RolesDashboardSerializer(serializers.ModelSerializer):

    class Meta:
        model = Roles
        # exclude = ('password',)
        # extra_fields = ['total_karma']
        fields = "__all__"
        read_only_fields = ["id", "created_at", 'updated_by','updated_at']