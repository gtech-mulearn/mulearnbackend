"""Helpers shared by the problem statement company, admin and learner views."""
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from db.problem_statement import ProblemStatement, ProblemStatementInteraction
from utils.response import CustomResponse

EDITABLE_FIELDS = ("title", "description", "category", "skills", "deadline")


def failure(message, status_code=400):
    return CustomResponse(general_message=message).get_failure_response(
        status_code=status_code, http_status_code=status_code
    )


def not_found():
    return failure("Problem statement not found.", 404)


def statement_queryset():
    return ProblemStatement.objects.select_related("company")


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


def my_interactions(user_id, statement_ids):
    return dict(
        ProblemStatementInteraction.objects.filter(
            user_id=user_id, problem_statement_id__in=statement_ids
        ).values_list("problem_statement_id", "status")
    )


# The three writers below lock the row and save only the columns they change, so a
# concurrent edit / publish can never overwrite the other's fields with stale values.

def apply_changes(statement_id, data, user_id):
    """Returns an error response, or None on success."""
    with transaction.atomic():
        statement = ProblemStatement.objects.select_for_update().filter(id=statement_id).first()
        if not statement:
            return not_found()
        changed = [field for field in EDITABLE_FIELDS if field in data]
        for field in changed:
            setattr(statement, field, data[field])
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
        if statement.deadline and statement.deadline <= timezone.now():
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
