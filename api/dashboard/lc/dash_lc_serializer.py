from rest_framework import serializers
from db.learning_circle import LearningCircle
class LearningCircleSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='created_by.fullname')
    updated_by = serializers.CharField(source='updated_by.fullname')
    ig = serializers.CharField(source='ig.name')
    org = serializers.CharField(source='org.title')
    class Meta:
        model = LearningCircle
        fields = [
            "id",
            "name",
            "circle_code",
            "ig",
            "org",
            "meet_place",
            "meet_time",
            "updated_by",
            "updated_at",
            "created_by",
            "created_at"
        ]
