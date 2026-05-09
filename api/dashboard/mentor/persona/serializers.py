from rest_framework import serializers
from db.user import UserRoleLink, UserMentor
from db.task import InterestGroup


class PersonaSwitchSerializer(serializers.Serializer):
    active_role_link_id = serializers.CharField(max_length=36)
    active_ig_id = serializers.CharField(max_length=36)

    def validate(self, data):
        user = self.context['user']

        # Ownership + activity check in a single query
        role_link = UserRoleLink.objects.select_related('ig', 'role').filter(
            id=data['active_role_link_id'],
            user=user,
            ig_id=data['active_ig_id'],
            is_active=True,
        ).first()

        if not role_link:
            raise serializers.ValidationError(
                "No active mentor role found for this IG, "
                "or you do not own this role assignment."
            )

        if role_link.role.title != 'Mentor':
            raise serializers.ValidationError(
                "The selected role link is not a Mentor role."
            )

        data['role_link'] = role_link
        return data


class IGRoleItemSerializer(serializers.ModelSerializer):
    role_link_id = serializers.CharField(source='id')
    ig_id = serializers.CharField(source='ig.id')
    ig_name = serializers.CharField(source='ig.name')
    role = serializers.CharField(source='role.title')
    is_verified = serializers.SerializerMethodField()
    mentor_tier = serializers.SerializerMethodField()

    class Meta:
        model = UserRoleLink
        fields = ['role_link_id', 'ig_id', 'ig_name', 'role', 'is_primary', 'is_verified', 'mentor_tier']

    def get_is_verified(self, obj):
        mentor = self.context.get('mentor_profile')
        if mentor:
            return mentor.is_verified
        return False

    def get_mentor_tier(self, obj):
        mentor = self.context.get('mentor_profile')
        if mentor:
            return mentor.mentor_tier
        return 'NORMAL'
