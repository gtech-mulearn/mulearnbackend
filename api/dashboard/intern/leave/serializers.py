from rest_framework import serializers
from django.utils.timezone import now
from datetime import timedelta
from db.intern import InternLeaveRequest
from utils.intern_permissions import (
    covering_membership, current_membership, team_ref, user_ref, working_membership_error,
)
from utils.types import InternLeaveStatus, InternLeaveType

MAX_LEAVE_DURATION_DAYS = 30
MAX_DAYS_IN_PAST = 30
MAX_DAYS_IN_FUTURE = 90

class InternLeaveRequestSerializer(serializers.ModelSerializer):
    leave_type = serializers.ChoiceField(choices=[t.value for t in InternLeaveType])

    class Meta:
        model = InternLeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason', 'duration_days']
        extra_kwargs = {
            'duration_days': {'required': False, 'allow_null': True}
        }

    def validate(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        today = now().date()
        user_id = self.context.get('user_id')

        # Active intern check: a current membership that isn't INACTIVE. The leave
        # belongs to the team the intern is in when requesting.
        if user_id:
            link = current_membership(user_id)
            error = working_membership_error(link)
            if error:
                raise serializers.ValidationError(
                    "You must be an active intern to request leave." if error == "Not an active intern." else error
                )
            # Backdated leave must start on a day they were in the program (any stint,
            # so the day before a reassign is fine).
            if start_date and start_date < link.join_date and covering_membership(user_id, start_date) is None:
                raise serializers.ValidationError(
                    {"start_date": "You weren't in the program on that date."}
                )
            # Leave can't run past the end of the tenure.
            if end_date and link.end_date and end_date > link.end_date:
                raise serializers.ValidationError(
                    {"end_date": f"Leave can't go past the end of your internship ({link.end_date:%d %b %Y})."}
                )
            data['team_id'] = link.team_id

        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError({"start_date": "Start date must be before or equal to end date."})

            # Date range limits
            if start_date < today - timedelta(days=MAX_DAYS_IN_PAST):
                raise serializers.ValidationError({"start_date": f"Leave cannot be requested more than {MAX_DAYS_IN_PAST} days in the past."})
            if end_date > today + timedelta(days=MAX_DAYS_IN_FUTURE):
                raise serializers.ValidationError({"end_date": f"Leave cannot be requested more than {MAX_DAYS_IN_FUTURE} days in the future."})

            # Duration limit
            duration = (end_date - start_date).days + 1
            if duration > MAX_LEAVE_DURATION_DAYS:
                raise serializers.ValidationError(
                    {"end_date": f"A single leave request cannot exceed {MAX_LEAVE_DURATION_DAYS} consecutive days."}
                )

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
                data['duration_days'] = duration
        return data

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        validated_data['user_id'] = user_id
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id
        validated_data['status'] = InternLeaveStatus.PENDING.value
        return super().create(validated_data)

class InternLeaveHistorySerializer(serializers.ModelSerializer):
    # The team the leave was requested in (null before teams) and who reviewed it.
    team = serializers.SerializerMethodField()
    reviewed_by = serializers.SerializerMethodField()

    class Meta:
        model = InternLeaveRequest
        fields = [
            'id', 'leave_type', 'start_date', 'end_date', 'reason', 'team',
            'status', 'review_note', 'reviewed_by', 'reviewed_at', 'created_at'
        ]

    def get_team(self, obj):
        return team_ref(obj.team)

    def get_reviewed_by(self, obj):
        return user_ref(obj.reviewed_by)
