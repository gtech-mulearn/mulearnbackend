from rest_framework import serializers
from db.achievement import Achievement, UserAchievements
# from db.user import User

class AchievementSerializer(serializers.ModelSerializer):

    class Meta:
        model = Achievement
        fields = '__all__'

class AchievementBasicSerializer(serializers.ModelSerializer):
    achievement_title = serializers.CharField(source="title")

    class Meta:
        model = Achievement
        fields = ['id', 'achievement_title', 'description', 'icon', 'level_based', 'tags']

class UserAchievementsSerializer(serializers.ModelSerializer):
    achievement_id = AchievementBasicSerializer(read_only=True)

    class Meta:
        model = UserAchievements
        fields = ['id', 'user_id', 'achievement_id', 'is_issued', 'vc_url']