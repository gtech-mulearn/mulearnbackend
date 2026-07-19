from rest_framework import serializers
from django.utils.timezone import now
from datetime import timedelta
from db.intern import InternLeaveRequest, UserInternGuildLink
from utils.types import InternLeaveStatus, InternLeaveType, InternGuildStatus

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

        # Active intern check
        if user_id:
            guild_link = UserInternGuildLink.objects.filter(user_id=user_id).first()
            if not guild_link or guild_link.status == InternGuildStatus.INACTIVE.value:
                raise serializers.ValidationError("You must be an active intern to request leave.")

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
    class Meta:
        model = InternLeaveRequest
        fields = [
            'id', 'leave_type', 'start_date', 'end_date', 'reason',
            'status', 'review_note', 'created_at'
        ]
