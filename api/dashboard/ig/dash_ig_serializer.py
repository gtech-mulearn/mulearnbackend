from rest_framework import serializers
from db.task import InterestGroup

class InterestGroupSerializer(serializers.ModelSerializer):
    updated_by = serializers.CharField(source='updated_by.fullname')
    created_by = serializers.CharField(source='created_by.fullname')
    count = serializers.SerializerMethodField()
    class Meta:
        model = InterestGroup
        fields = [
            "id",
            "name",
            "count",
            "updated_by",
            "updated_at",
            "created_by",
            "created_at",
        ]
    
    def get_count(self, obj):
        return len(obj.user_ig_link_ig.all())
