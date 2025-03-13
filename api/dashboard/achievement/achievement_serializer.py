from rest_framework import serializers
from db.achievement import Achievement
# from db.user import User

class AchievementSerializer(serializers.ModelSerializer):

    class Meta:
        model = Achievement
        fields = '__all__'


