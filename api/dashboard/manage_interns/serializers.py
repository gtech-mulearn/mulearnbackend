from rest_framework import serializers
from db.intern import UserInternGuildLink
from utils.types import InternGuildStatus

class ManageInternSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.fullname', read_only=True)
    muid = serializers.CharField(source='user.muid', read_only=True)
    
    class Meta:
        model = UserInternGuildLink
        fields = ['id', 'user', 'full_name', 'muid', 'guild', 'status', 'created_at']

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id
        if 'status' not in validated_data:
            validated_data['status'] = InternGuildStatus.ACTIVE.value
        return super().create(validated_data)

    def update(self, instance, validated_data):
        user_id = self.context.get('user_id')
        validated_data['updated_by_id'] = user_id
        return super().update(instance, validated_data)
