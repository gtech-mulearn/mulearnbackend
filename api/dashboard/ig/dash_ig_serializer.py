from rest_framework import serializers
from db.task import InterestGroup

class InterestGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterestGroup
        fields = [
            "id",
            "name",
            "updated_by",
            "updated_at",
            "created_by",
            "created_at",
        ]
