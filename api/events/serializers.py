import uuid
from rest_framework import serializers
from db.task import UnifiedEvent

class UnifiedEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnifiedEvent
        fields = [
            'id', 'type', 'created_by', 'campus', 'ig', 'title', 
            'description', 'date', 'location', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        validated_data['id'] = str(uuid.uuid4())
        validated_data['created_by_id'] = user_id
        return super().create(validated_data)
