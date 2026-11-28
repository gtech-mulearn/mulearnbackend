from rest_framework import serializers
from db.intern import InternTask
from utils.intern_permissions import team_ref

COMPLEXITY_WEIGHT_MAP = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 5}


class InternTaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    complexity_score = serializers.SerializerMethodField()
    # The team the task was assigned in (null on tasks from before teams).
    team = serializers.SerializerMethodField()

    class Meta:
        model = InternTask
        fields = [
            'id', 'title', 'description', 'category', 'complexity',
            'complexity_score', 'assigned_to', 'assigned_to_name', 'status',
            'remark', 'team', 'karma_awarded', 'output_link', 'is_verified', 'verified_by',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['remark']

    def get_complexity_score(self, obj):
        return COMPLEXITY_WEIGHT_MAP.get(obj.complexity, 1)

    def get_team(self, obj):
        return team_ref(obj.team)
