from rest_framework import serializers
from db.intern import InternLeaveRequest
from utils.types import InternLeaveStatus

class InternLeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternLeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason', 'duration_days']
        extra_kwargs = {
            'duration_days': {'required': False, 'allow_null': True}
        }

    def validate(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError({"start_date": "Start date must be before or equal to end date."})
            
            user_id = self.context.get('user_id')
            if user_id:
                overlapping_leaves = InternLeaveRequest.objects.filter(
                    user_id=user_id,
                    status__in=[InternLeaveStatus.PENDING.value, InternLeaveStatus.APPROVED.value],
                    start_date__lte=end_date,
                    end_date__gte=start_date
                ).exists()
                
                if overlapping_leaves:
                    raise serializers.ValidationError(
                        {"date_range": "You already have a pending or approved leave request during this period."}
                    )
            
            if 'duration_days' not in data or data.get('duration_days') is None:
                data['duration_days'] = (end_date - start_date).days + 1
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
