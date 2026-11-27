from rest_framework import serializers
from db.intern import InternLeaveRequest
from utils.intern_permissions import team_ref, user_ref


class ManageInternLeaveSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_muid = serializers.CharField(source='user.muid', read_only=True)
    # The team the leave was requested in (null before teams) and who reviewed it.
    team = serializers.SerializerMethodField()
    reviewed_by = serializers.SerializerMethodField()

    class Meta:
        model = InternLeaveRequest
        fields = [
            'id', 'user', 'user_name', 'user_muid', 'team', 'leave_type', 'start_date', 'end_date', 'reason',
            'status', 'review_note', 'reviewed_by', 'reviewed_at', 'created_at'
        ]

    def get_team(self, obj):
        return team_ref(obj.team)

    def get_reviewed_by(self, obj):
        return user_ref(obj.reviewed_by)
