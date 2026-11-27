from django.db.models import Prefetch
from rest_framework import serializers

from db.intern import InternTeam, UserInternTeamLink
from db.user import User, UserRoleLink
from utils.intern_permissions import LEAD_ROLE, MEMBER_ROLES, ist_today, tenure_state
from utils.types import InternStatus

MAX_REASSIGN = 200
REASON_MAX_LENGTH = 300


def intern_queryset():
    """Membership rows with everything ManageInternSerializer reads, in a fixed number of queries."""
    return (
        UserInternTeamLink.objects
        .select_related('user', 'team')
        .prefetch_related(Prefetch(
            'user__user_role_link_user',
            queryset=UserRoleLink.objects.filter(role__title__in=MEMBER_ROLES).select_related('role'),
            to_attr='intern_role_links',
        ))
    )


def intern_roles(link):
    """Intern-type role titles the user holds, using the prefetch when present."""
    prefetched = getattr(link.user, 'intern_role_links', None)
    if prefetched is not None:
        titles = {rl.role.title for rl in prefetched}
    else:
        titles = set(
            UserRoleLink.objects.filter(user_id=link.user_id, role__title__in=MEMBER_ROLES)
            .values_list('role__title', flat=True)
        )
    # Stable order: Intern first, then Intern Lead.
    return [title for title in MEMBER_ROLES if title in titles]


class ManageInternSerializer(serializers.ModelSerializer):
    """Read shape of one intern membership row. Use with intern_queryset()."""
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    muid = serializers.CharField(source='user.muid', read_only=True)
    team = serializers.SerializerMethodField()
    # The API keeps the key `status`; the column is intern_status.
    status = serializers.CharField(source='intern_status', read_only=True)
    is_lead = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    # UPCOMING (before join_date), ACTIVE or ENDED (after end_date), and days until end_date.
    tenure_state = serializers.SerializerMethodField()
    days_left = serializers.SerializerMethodField()

    class Meta:
        model = UserInternTeamLink
        # The membership row id isn't sent: no endpoint takes it. Rows are keyed by `user`.
        fields = [
            'user', 'full_name', 'muid', 'team', 'status', 'status_reason',
            'join_date', 'end_date', 'tenure_state', 'days_left',
            'is_current', 'exit_reason', 'is_lead', 'roles', 'created_at',
        ]

    def get_tenure_state(self, obj):
        return tenure_state(obj)

    def get_days_left(self, obj):
        return max((obj.end_date - ist_today()).days, 0) if obj.end_date else None

    def get_team(self, obj):
        return {"id": obj.team.id, "name": obj.team.name, "code": obj.team.code}

    def get_roles(self, obj):
        return intern_roles(obj)

    def get_is_lead(self, obj):
        return LEAD_ROLE in intern_roles(obj)


class OnboardInternSerializer(serializers.Serializer):
    mu_id = serializers.CharField(required=False, allow_blank=False)
    user_id = serializers.CharField(required=False, allow_blank=False)
    team_id = serializers.CharField(required=True)
    # The tenure: join_date can't be in the past, end_date not before join_date
    # (checked in onboard_intern).
    join_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)

    def validate(self, attrs):
        mu_id = attrs.get('mu_id')
        user_id = attrs.get('user_id')
        if not mu_id and not user_id:
            raise serializers.ValidationError({"user": "Either user_id or mu_id is required."})

        if mu_id:
            user = User.objects.filter(muid=mu_id).first()
            if not user:
                raise serializers.ValidationError({"mu_id": "No user found with this mu_id."})
        else:
            user = User.objects.filter(id=user_id).first()
            if not user:
                raise serializers.ValidationError({"user_id": "No user found with this user_id."})

        team = InternTeam.objects.filter(id=attrs['team_id']).first()
        if not team:
            raise serializers.ValidationError({"team_id": "Team not found."})

        attrs['user'] = user
        attrs['team'] = team
        return attrs


class UpdateInternSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[s.value for s in InternStatus], required=False
    )
    is_lead = serializers.BooleanField(required=False)
    # New planned end of the tenure (Admin: any date from today; Lead: only later).
    end_date = serializers.DateField(required=False)
    # Why the status changed: required whenever status is sent, saved to status_reason.
    reason = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=REASON_MAX_LENGTH
    )

    def validate(self, attrs):
        if 'reason' in attrs:
            attrs['reason'] = (attrs['reason'] or '').strip() or None
        if not {'status', 'is_lead', 'end_date'} & attrs.keys():
            raise serializers.ValidationError({"detail": "Send is_lead and/or end_date."})
        if 'status' in attrs and not attrs.get('reason'):
            raise serializers.ValidationError({"reason": "A reason is required to change an intern's status."})
        if attrs.get('reason') and 'status' not in attrs:
            raise serializers.ValidationError({"reason": "A reason can only be given with a status change."})
        if attrs.get('status') == InternStatus.ON_LEAVE.value:
            # ON_LEAVE comes only from approved leave requests, so every leave has dates.
            raise serializers.ValidationError(
                {"status": "ON_LEAVE can't be set by hand. Approve a leave request instead."}
            )
        if attrs.get('status') == InternStatus.INACTIVE.value and attrs.get('is_lead') is True:
            raise serializers.ValidationError(
                {"is_lead": "An intern being deactivated can't be made a Lead."}
            )
        return attrs


class DeactivateInternSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=True, allow_blank=False, max_length=REASON_MAX_LENGTH,
        error_messages={
            "required": "A reason is required to deactivate an intern.",
            "blank": "A reason is required to deactivate an intern.",
        },
    )


class ReassignInternsSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.CharField(), allow_empty=False, max_length=MAX_REASSIGN
    )
    team_id = serializers.CharField(required=True)
    # The planned end in the new team, one date for everyone in the list.
    end_date = serializers.DateField(required=True)

    def validate(self, attrs):
        team = InternTeam.objects.filter(id=attrs['team_id']).first()
        if not team:
            raise serializers.ValidationError({"team_id": "Team not found."})
        if not team.is_active:
            raise serializers.ValidationError({"team_id": f"{team.name} ({team.code}) is inactive. Activate it first."})
        attrs['team'] = team
        attrs['user_ids'] = list(dict.fromkeys(attrs['user_ids']))
        return attrs
