import re

from rest_framework import serializers

from db.intern import InternTeam

CODE_PATTERN = re.compile(r'^[A-Z0-9]{2,10}$')


class InternTeamSerializer(serializers.ModelSerializer):
    """
    Read shape for a team. Expects the queryset to be annotated with
    `member_count` and `active_member_count` (see teams_views.annotate_counts)
    and `context['leads_by_team']` to map team id -> list of lead dicts.
    """
    member_count = serializers.IntegerField(read_only=True, default=0)
    active_member_count = serializers.IntegerField(read_only=True, default=0)
    leads = serializers.SerializerMethodField()

    class Meta:
        model = InternTeam
        fields = [
            'id', 'name', 'code', 'description', 'is_active', 'deactivated_at',
            'member_count', 'active_member_count', 'leads',
            'created_at', 'updated_at',
        ]

    def get_leads(self, obj):
        return self.context.get('leads_by_team', {}).get(obj.id, [])


class InternTeamWriteSerializer(serializers.ModelSerializer):
    """
    Create/update input. The name can repeat; the code is unique ignoring case across
    every team, active or inactive, and is stored uppercase.
    """
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = InternTeam
        fields = ['name', 'code', 'description']

    def _others(self):
        qs = InternTeam.objects.all()
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        return qs

    def validate_name(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError("Team name is required.")
        return value

    def validate_code(self, value):
        value = (value or '').strip().upper()
        if not CODE_PATTERN.match(value):
            raise serializers.ValidationError("Code must be 2-10 letters or digits.")
        existing = self._others().filter(code__iexact=value).first()
        if existing:
            if existing.is_active:
                raise serializers.ValidationError(f"Code '{value}' is already used by {existing.name}.")
            raise serializers.ValidationError(
                f"Code '{value}' is already used by {existing.name} (inactive). Activate it instead."
            )
        return value

    def validate_description(self, value):
        if value is None:
            return None
        value = value.strip()
        return value or None
