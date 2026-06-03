from rest_framework import serializers
from db.intern import InternLeaveRequest
from utils.types import InternLeaveStatus

class InternLeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternLeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason']

    def validate(self, data):
        if data.get('start_date') > data.get('end_date'):
            raise serializers.ValidationError({"start_date": "Start date must be before or equal to end date."})
        return data

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        validated_data['user_id'] = user_id
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id
        validated_data['status'] = InternLeaveStatus.PENDING.value
        return super().create(validated_data)

class InternLeaveHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InternLeaveRequest
        fields = [
            'id', 'leave_type', 'start_date', 'end_date', 'reason',
            'status', 'review_note', 'created_at'
        ]
