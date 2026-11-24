"""Helpers shared by the problem statement company, admin and learner views."""
import logging

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from db.user import User
from db.problem_statement import ProblemStatement, ProblemStatementInteraction
from utils.response import CustomResponse

logger = logging.getLogger(__name__)

EDITABLE_FIELDS = ("title", "description", "category", "skills", "deadline")


def failure(message, status_code=400):
    return CustomResponse(general_message=message).get_failure_response(
        status_code=status_code, http_status_code=status_code
    )


def not_found():
    return failure("Problem statement not found.", 404)


def statement_queryset():
    return ProblemStatement.objects.select_related("company", "on_behalf_of")


def filter_source(qs, params):
    """Apply ``?source=company|mulearn``; any other value is ignored."""
    source = params.get("source")
    if source in ProblemStatement.Source.values:
        qs = qs.filter(source=source)
    return qs


def deadline_passed(statement):
    return statement.deadline is not None and statement.deadline <= timezone.now()


def lock_statement(statement_id):
    """
    Lock and re-read the statement row; must run inside ``transaction.atomic``.

    Every write that depends on the statement's status or deadline locks this row
    first and checks against the value it returns, after any lock wait. Edits,
    publish/unpublish and delete take the same lock, so the deadline or status
    can't change between the check and the write, and every writer locks the
    statement before any interaction row (one lock order, no deadlocks).
    """
    return ProblemStatement.objects.select_for_update().filter(id=statement_id).first()


def interaction_counts(statement_ids):
    """{statement_id: {status: n}} for the given ids in a single query."""
    rows = (
        ProblemStatementInteraction.objects.filter(problem_statement_id__in=statement_ids)
        .values("problem_statement_id", "status")
        .annotate(n=Count("id"))
    )
    result = {}
    for row in rows:
        result.setdefault(row["problem_statement_id"], {})[row["status"]] = row["n"]
    return result


def counts_for(statement_id):
    """Counts for one statement, with every status present (0 when none)."""
    counts = interaction_counts([statement_id]).get(statement_id, {})
    return {status: counts.get(status, 0) for status in ProblemStatementInteraction.Status.values}


def my_interactions(user_id, statement_ids):
    return dict(
        ProblemStatementInteraction.objects.filter(
            user_id=user_id, problem_statement_id__in=statement_ids
        ).values_list("problem_statement_id", "status")
    )


# The three writers below lock the row and save only the columns they change, so a
# concurrent edit / publish can never overwrite the other's fields with stale values.

_UNSET = object()


def resolve_muid(raw):
    """
    (user_id, error). ``None``/blank clears the mention (user_id None). An unknown muid is a 400.
    Suspended users are excluded (``User.objects``): they can't receive the notification.
    """
    muid = (raw or "").strip()
    if not muid:
        return None, None
    user_id = User.objects.filter(muid=muid).values_list("id", flat=True).first()
    if not user_id:
        return None, failure("No user found with this muid.")
    return user_id, None


def notify_on_behalf_of(user_id, statement, actor_id):
    """Best-effort in-app notification; a failure here must never fail the write."""
    if not user_id or user_id == actor_id:
        return
    try:
        from api.notification.notifications_utils import NotificationUtils
        NotificationUtils.insert_notification(
            user=User.objects.get(id=user_id),
            title="Problem statement created for you",
            description=f'A problem statement "{statement.title}" was created on your behalf.',
            button="View", url=None, created_by_id=actor_id,
        )
    except Exception:
        logger.exception("Failed to notify on-behalf-of user for problem statement %s", statement.id)


def apply_changes(statement_id, data, user_id, on_behalf_of_id=_UNSET):
    """Returns an error response, or None on success. ``on_behalf_of_id`` None clears the mention."""
    with transaction.atomic():
        statement = ProblemStatement.objects.select_for_update().filter(id=statement_id).first()
        if not statement:
            return not_found()
        changed = [field for field in EDITABLE_FIELDS if field in data]
        for field in changed:
            setattr(statement, field, data[field])
        if on_behalf_of_id is not _UNSET:
            statement.on_behalf_of_id = on_behalf_of_id
            changed.append("on_behalf_of")
        statement.updated_by_id = user_id
        statement.save(update_fields=[*changed, "updated_by", "updated_at"])
    return None


def publish(statement_id, user_id):
    with transaction.atomic():
        statement = ProblemStatement.objects.select_for_update().filter(id=statement_id).first()
        if not statement:
            return not_found()
        if statement.status == ProblemStatement.Status.PUBLISHED:
            return failure("Problem statement is already published.", 409)
        if deadline_passed(statement):
            return failure("Cannot publish a problem statement whose deadline has passed.", 409)
        statement.status = ProblemStatement.Status.PUBLISHED
        statement.published_by_id = user_id
        statement.published_at = timezone.now()
        statement.updated_by_id = user_id
        statement.save(update_fields=[
            "status", "published_by", "published_at", "updated_by", "updated_at",
        ])
    return None


def unpublish(statement_id, user_id):
    with transaction.atomic():
        statement = ProblemStatement.objects.select_for_update().filter(id=statement_id).first()
        if not statement:
            return not_found()
        if statement.status != ProblemStatement.Status.PUBLISHED:
            return failure("Only a published problem statement can be unpublished.", 409)
        statement.status = ProblemStatement.Status.UNPUBLISHED
        statement.updated_by_id = user_id
        statement.save(update_fields=["status", "updated_by", "updated_at"])
    return None
