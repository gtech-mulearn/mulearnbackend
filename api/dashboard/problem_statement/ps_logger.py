import uuid
from db.problem_statement import ProblemStatementAuditLog

FIELD_LABELS = {
    'title': 'Title',
    'description': 'Description',
    'company': 'Company',
    'company_id': 'Company',
    'level': 'Level',
    'type': 'Type',
    'status': 'Status',
    'deadline': 'Deadline',
    'hashtag': 'Hashtag',
    'is_featured': 'Featured',
    'is_active': 'Active',
}


def _serialize_value(value):
    """Convert a value to JSON-serializable format."""
    if value is None:
        return None
    if hasattr(value, 'pk') and hasattr(value, '__str__'):
        return {'id': str(value.pk), 'name': str(value)}
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


def build_diff(instance, validated_data):
    """
    Compare incoming `validated_data` against current `instance` values.
    Returns a dict of changed fields:
    {
        "Title": {"from": "old", "to": "new"}
    }
    """
    changes = {}
    for field, new_value in validated_data.items():
        label = FIELD_LABELS.get(field, field.replace('_', ' ').title())

        try:
            old_value = getattr(instance, field)
        except AttributeError:
            old_value = None

        serialized_old = _serialize_value(old_value)
        serialized_new = _serialize_value(new_value)

        if serialized_old != serialized_new:
            changes[label] = {
                'from': serialized_old,
                'to': serialized_new,
            }

    return changes


def log_ps_action(problem_statement, action, actor_id, actor_role=None, metadata=None):
    """
    Create a ProblemStatementAuditLog record synchronously.

    Args:
        problem_statement: ProblemStatement instance
        action: ProblemStatementAuditLog.Action choice or string
        actor_id: str UUID or User instance
        actor_role: str (e.g. "System/Cron", "System Admin", "Company Owner")
        metadata: dict (optional)
    """
    if hasattr(actor_id, 'id'):
        actor_id_val = str(actor_id.id)
    else:
        actor_id_val = str(actor_id)

    ps_id = str(problem_statement.id)

    return ProblemStatementAuditLog.objects.create(
        id=str(uuid.uuid4()),
        problem_statement=problem_statement,
        target_type='problem_statement',
        target_id=ps_id,
        action=action,
        actor_id=actor_id_val,
        actor_role=actor_role,
        metadata=metadata,
    )
