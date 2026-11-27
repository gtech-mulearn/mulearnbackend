from rest_framework import serializers
from django.utils.timezone import now
from db.intern import InternTask
from db.user import User
from utils.intern_permissions import caller_team_id, current_membership, is_admin, team_ref, working_membership_error

COMPLEXITY_WEIGHT_MAP = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 5}

class UserPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def to_internal_value(self, data):
        # Try to retrieve user by muid first, then fallback to uuid (pk)
        user = User.objects.filter(muid=data).first()
        if user:
            return user
        try:
            return super().to_internal_value(data)
        except serializers.ValidationError:
            raise serializers.ValidationError(
                f"User with muid or user_id '{data}' does not exist."
            )

class ManageInternTaskSerializer(serializers.ModelSerializer):
    assigned_to = UserPrimaryKeyRelatedField(queryset=User.objects.all())
    # Accepted so older clients that still send it don't get "Unknown field.",
    # but always derived from the deadline in validate().
    iso_week = serializers.IntegerField(required=False)
    is_verified = serializers.BooleanField(required=False)
    complexity = serializers.ChoiceField(
        choices=['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'],
        default='LOW'
    )
    complexity_score = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    assigned_to_muid = serializers.SerializerMethodField()
    # The team the task was assigned in (null on tasks from before teams). Set from
    # the assignee's current team; not accepted from the client.
    team = serializers.SerializerMethodField()

    class Meta:
        model = InternTask
        fields = [
            'id', 'title', 'description', 'category', 'complexity',
            'complexity_score', 'assigned_to', 'assigned_to_name', 'assigned_to_muid',
            'status', 'remark', 'team', 'deadline', 'iso_week', 'output_link',
            'karma_awarded', 'is_verified', 'verified_by_id', 'created_at'
        ]
        # karma_awarded is set only by the verify endpoint (and reset when verification is
        # revoked), so it can't be written through create or update.
        read_only_fields = ['created_at', 'verified_by_id', 'karma_awarded']

    def get_complexity_score(self, obj):
        return COMPLEXITY_WEIGHT_MAP.get(obj.complexity, 1)

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.full_name if obj.assigned_to else None

    def get_assigned_to_muid(self, obj):
        return obj.assigned_to.muid if obj.assigned_to else None

    def get_team(self, obj):
        return team_ref(obj.team)

    def validate(self, attrs):
        # The assignee must be a current member who isn't INACTIVE; a Lead may only
        # assign to members of their own team. The task belongs to the assignee's
        # current team. Re-checked only when the assignee changes on an update.
        assigned_to = attrs.get('assigned_to')
        if assigned_to and (not self.instance or assigned_to.id != self.instance.assigned_to_id):
            link = current_membership(assigned_to.id)
            if working_membership_error(link):
                # Not a member, INACTIVE, not started yet or tenure ended.
                raise serializers.ValidationError(
                    {"assigned_to": f"User '{assigned_to.muid}' is not an active intern."}
                )
            request = self.context.get('request')
            if request is not None and not is_admin(request) and link.team_id != caller_team_id(request):
                raise serializers.ValidationError(
                    {"assigned_to": "You can only assign tasks to members of your own team."}
                )
            attrs['team_id'] = link.team_id

        # Prevent creating tasks with a past deadline (only on create, not update)
        if not self.instance and 'deadline' in attrs:
            if attrs['deadline'] < now().date():
                raise serializers.ValidationError(
                    {"deadline": "Task deadline cannot be in the past."}
                )

        # iso_week is always the deadline's ISO week; a client-sent value is ignored.
        # The timesheet prefill matches tasks on iso_week plus the deadline's ISO
        # year (there is no year column), so the two must never disagree.
        attrs.pop('iso_week', None)
        if 'deadline' in attrs:
            attrs['iso_week'] = attrs['deadline'].isocalendar()[1]

        # Block direct verification via PATCH — must use the /verify/ endpoint
        if attrs.get('is_verified') is True:
            raise serializers.ValidationError(
                "Task verification must be done via the dedicated verification endpoint."
            )

        return attrs

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id

        return super().create(validated_data)

    def update(self, instance, validated_data):
        from django.db import transaction
        from django.db.models import F
        from django.utils.timezone import now
        from db.task import KarmaActivityLog, TaskList, Wallet
        from utils.types import InternHashtag

        user_id = self.context.get('user_id')
        validated_data['updated_by_id'] = user_id

        # Determine if we should revert verification:
        # Either admin explicitly sets is_verified=False, or changes the task status
        new_is_verified = validated_data.get('is_verified')
        new_status = validated_data.get('status')

        should_revert = (
            instance.is_verified and (
                new_is_verified is False or
                (new_status is not None and new_status != instance.status)
            )
        ) 

        if should_revert:
            with transaction.atomic():
                if instance.karma_awarded > 0:
                    # Deduct karma from the intern's wallet
                    Wallet.objects.filter(user_id=instance.assigned_to_id).update(
                        karma=F('karma') - instance.karma_awarded
                    )

                    # Delete the corresponding KarmaActivityLog entry
                    task_list = TaskList.objects.filter(
                        hashtag=InternHashtag.TASK_VERIFIED_HASHTAG.value
                    ).first()
                    if task_list:
                        # Primary lookup: by intern task ID stored in task_message_id
                        karma_log = KarmaActivityLog.objects.filter(
                            user_id=instance.assigned_to_id,
                            task=task_list,
                            task_message_id=instance.id
                        ).first()
                        # Fallback for older entries without task_message_id
                        if not karma_log:
                            karma_log = KarmaActivityLog.objects.filter(
                                user_id=instance.assigned_to_id,
                                task=task_list,
                                karma=instance.karma_awarded
                            ).order_by('-created_at').first()
                        if karma_log:
                            karma_log.delete()

                # Reset verification fields
                validated_data['is_verified'] = False
                validated_data['verified_by_id'] = None
                validated_data['karma_awarded'] = 0

        return super().update(instance, validated_data)
