from rest_framework import serializers
from db.intern import InternLeaveRequest

class ManageInternLeaveSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_muid = serializers.CharField(source='user.muid', read_only=True)

    class Meta:
        model = InternLeaveRequest
        fields = [
            'id', 'user', 'user_name', 'user_muid', 'leave_type', 'start_date', 'end_date', 'reason',
            'status', 'review_note', 'created_at'
        ]

