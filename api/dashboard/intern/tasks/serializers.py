from rest_framework import serializers
from db.intern import InternTask

class InternTaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = InternTask
        fields = [
            'id', 'title', 'description', 'category', 'complexity',
            'assigned_to', 'assigned_to_name', 'status',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
