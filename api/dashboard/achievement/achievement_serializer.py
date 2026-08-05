from rest_framework import serializers
from django.conf import settings
from db.achievement import Achievement, UserAchievementsLog
# from db.user import User

class AchievementSerializer(serializers.ModelSerializer):
    icon_url = serializers.SerializerMethodField()
    has_achievement = serializers.SerializerMethodField()

    class Meta:
        model = Achievement
        fields = '__all__'

    def get_icon_url(self, obj):
        if obj.icon:
            # Check if it's already a full URL
            if obj.icon.startswith('http://') or obj.icon.startswith('https://'):
                return obj.icon
            # Build full URL with domain
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(f"{settings.MEDIA_URL}{obj.icon}")
            # Fallback: return media path (frontend will need to prepend backend URL)
            return f"{settings.MEDIA_URL}{obj.icon}"
        return None

    def get_has_achievement(self, obj):
        """
        Returns True if the user (passed in context as 'user_achievements')
        already holds this achievement, otherwise False.
        """
        user_achievements = self.context.get('user_achievements', set())
        return obj.id in user_achievements

class AchievementBasicSerializer(serializers.ModelSerializer):
    achievement_name = serializers.CharField(source='name')
    icon_url = serializers.SerializerMethodField()

    class Meta:
        model = Achievement
        fields = ['id', 'achievement_name', 'description', 'icon', 'icon_url', 'level_id', 'tags', 'template_id']
    
    def get_icon_url(self, obj):
        if obj.icon:
            if obj.icon.startswith('http://') or obj.icon.startswith('https://'):
                return obj.icon
            return f"{settings.MEDIA_URL}{obj.icon}"
        return None

class UserAchievementsSerializer(serializers.ModelSerializer):
    achievement = AchievementBasicSerializer(source='achievement_id', read_only=True)

    class Meta:
        model = UserAchievementsLog
        fields = ['id', 'user_id', 'achievement', 'is_issued', 'vc_url']
