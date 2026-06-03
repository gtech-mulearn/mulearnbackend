from rest_framework import serializers
from db.intern import InternTask

class ManageInternTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternTask
        fields = [
            'id', 'title', 'description', 'category', 'complexity',
            'assigned_to', 'status'
        ]

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id
        return super().create(validated_data)

    def update(self, instance, validated_data):
        user_id = self.context.get('user_id')
        validated_data['updated_by_id'] = user_id
        return super().update(instance, validated_data)
