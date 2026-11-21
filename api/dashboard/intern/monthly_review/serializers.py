from rest_framework import serializers

from db.intern import InternMonthlyReview, InternTask
from utils.types import InternSubmissionStatus, InternTaskStatus

from .leave import review_leave_days

# Free-text answers the intern gives; stored together in task_remarks.
REMARK_TEXT_FIELDS = ('learnings', 'challenges_faced', 'next_month_plan')
REMARK_LABELS = {
    'learnings': "Learnings",
    'challenges_faced': "Challenges Faced",
    'next_month_plan': "Next Month Plan",
}
COMPLETED_TASK_STATUSES = [InternTaskStatus.COMPLETED.value, InternTaskStatus.WAITING_FOR_REVIEW.value]


def month_tasks(user_id, window, completed_only=False):
    """The intern's non-archived tasks whose deadline falls inside the reviewed month."""
    tasks = InternTask.objects.filter(
        assigned_to_id=user_id,
        deadline__range=(window.period_start, window.period_end),
        is_archived=False,
    )
    if completed_only:
        tasks = tasks.filter(status__in=COMPLETED_TASK_STATUSES)
    return tasks.order_by('deadline')


def task_snapshot(task, status_key='final_status'):
    return {
        'task_id': str(task.id),
        'title': task.title,
        'category': task.category,
        'complexity': task.complexity,
        'deadline': task.deadline.isoformat(),
        status_key: task.status,
        'output_link': task.output_link,
    }


def _build_review_text(remarks):
    parts = [
        f"{REMARK_LABELS[key]}: {remarks[key]}"
        for key in REMARK_TEXT_FIELDS
        if remarks.get(key)
    ]
    return "\n\n".join(parts)


class InternMonthlyReviewSerializer(serializers.ModelSerializer):
    """
    Create / resubmit (partial=False) and edit (partial=True) a monthly review.

    Context:
        user_id:    the intern (from the JWT)
        window:     MonthlyReviewWindow being submitted for (must be open)
        team:       guild name to store
        resubmit:   True when replacing a REJECTED review in the same window
    """
    monthly_review = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=5000)
    rating = serializers.IntegerField(required=False, allow_null=True, write_only=True, min_value=1, max_value=5)
    learnings = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True, max_length=2000)
    challenges_faced = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True, max_length=2000)
    next_month_plan = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True, max_length=2000)
    blockers = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=2000)
    suggestions = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=2000)
    # leave_days is not stored: it is worked out on read from approved leave
    # (see leave.py). It is declared only so a form that still sends the
    # prefilled value isn't rejected by the project's strict-serializer patch
    # (mulearnbackend/__init__.py, "Unknown field."); validate() drops it.
    leave_days = serializers.JSONField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = InternMonthlyReview
        fields = [
            'monthly_review', 'rating', 'learnings', 'challenges_faced',
            'next_month_plan', 'blockers', 'leave_days', 'suggestions',
        ]

    def validate(self, data):
        data.pop('leave_days', None)
        # On an edit, fields not sent keep their stored values; on a create or
        # resubmit the form is taken as a whole.
        editing = bool(self.instance) and self.partial
        old_remarks = (self.instance.task_remarks or {}) if editing else {}

        remarks = {
            'rating': old_remarks.get('rating'),
            **{key: old_remarks.get(key) for key in REMARK_TEXT_FIELDS},
        }
        for key in ('rating',) + REMARK_TEXT_FIELDS:
            if key in data:
                value = data.pop(key)
                remarks[key] = value.strip() if isinstance(value, str) else value
                if remarks[key] == '':
                    remarks[key] = None

        text = data.get('monthly_review')
        text = text.strip() if text else ''
        if not text:
            if editing and 'monthly_review' not in data:
                # Keep the stored text, unless it was generated from the old
                # answers — then regenerate it so it stays in sync.
                stored = self.instance.monthly_review
                text = _build_review_text(remarks) if stored == _build_review_text(old_remarks) else stored
            else:
                text = _build_review_text(remarks)

        if not text:
            raise serializers.ValidationError({
                "monthly_review": "Write your monthly review, or fill in learnings, challenges faced or next month's plan."
            })

        data['monthly_review'] = text
        data['task_remarks'] = remarks
        return data

    def _server_fields(self):
        user_id = self.context['user_id']
        window = self.context['window']
        return {
            'tasks_completed': [
                task_snapshot(t) for t in month_tasks(user_id, window, completed_only=True)
            ],
            'updated_by_id': user_id,
        }

    def create(self, validated_data):
        user_id = self.context['user_id']
        window = self.context['window']
        validated_data.update(self._server_fields())
        validated_data.update({
            'user_id': user_id,
            'year': window.year,
            'month': window.month,
            'period_start': window.period_start,
            'period_end': window.period_end,
            'team': self.context.get('team') or '',
            'status': InternSubmissionStatus.PENDING.value,
            'created_by_id': user_id,
        })
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.update(self._server_fields())
        if self.context.get('resubmit'):
            # A rejected review is replaced as a whole and goes back for review.
            validated_data.setdefault('blockers', None)
            validated_data.setdefault('suggestions', None)
            validated_data.update({
                'team': self.context.get('team') or instance.team,
                'status': InternSubmissionStatus.PENDING.value,
                'reviewed_by': None,
                'reviewed_at': None,
                'review_note': None,
            })
        return super().update(instance, validated_data)


class InternMonthlyReviewHistorySerializer(serializers.ModelSerializer):
    # Approved leave days in the review month (WFH included), worked out on
    # read. List views pass context['leave_days'] from leave_days_by_review.
    leave_days = serializers.SerializerMethodField()

    class Meta:
        model = InternMonthlyReview
        fields = [
            'id', 'year', 'month', 'period_start', 'period_end', 'team',
            'tasks_completed', 'monthly_review', 'task_remarks', 'blockers',
            'leave_days', 'suggestions', 'status', 'review_note',
            'reviewed_at', 'created_at', 'updated_at',
        ]

    def get_leave_days(self, obj) -> int:
        return review_leave_days(self, obj)
