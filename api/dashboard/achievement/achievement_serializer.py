from rest_framework import serializers
from db.achievement import Achievement, UserAchievementsLog
# from db.user import User

class AchievementSerializer(serializers.ModelSerializer):

    class Meta:
        model = Achievement
        fields = '__all__'

class AchievementBasicSerializer(serializers.ModelSerializer):
    achievement_name = serializers.CharField(source='name')

    class Meta:
        model = Achievement
        fields = ['id', 'achievement_name', 'description', 'icon', 'level_id', 'tags', 'template_id']

class UserAchievementsSerializer(serializers.ModelSerializer):
    achievement = AchievementBasicSerializer(source='achievement_id', read_only=True)

    class Meta:
        model = UserAchievementsLog
        fields = ['id', 'user_id', 'achievement', 'is_issued', 'vc_url']
