"""Helpers shared by the problem statement company, admin and learner views."""
import logging

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from db.company import Company
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
    (user, error). ``None``/blank clears the mention (user None). An unknown muid is a 400.
    Suspended users are excluded (``User.objects``): they can't receive the notification.
    """
    muid = (raw or "").strip()
    if not muid:
        return None, None
    user = User.objects.filter(muid=muid).only("id").first()
    if not user:
        return None, failure("No user found with this muid.")
    return user, None


def notify_on_behalf_of(user, statement, actor_id, created):
    """
    Best-effort in-app notification; a failure here must never fail the write.
    No button/link: the statement may still be a Draft, which the user cannot open.
    """
    if user is None or user.id == actor_id:
        return
    try:
        from api.notification.notifications_utils import NotificationUtils
        if created:
            title = "Problem statement drafted for you"
            description = f'A problem statement "{statement.title}" was created on your behalf.'
        else:
            title = "Added to a problem statement"
            description = f'You were added to the problem statement "{statement.title}" as the person it is on behalf of.'
        NotificationUtils.insert_notification(
            user=user, title=title, description=description,
            button=None, url=None, created_by_id=actor_id,
        )
    except Exception:
        logger.exception("Failed to notify on-behalf-of user for problem statement %s", statement.id)


def resolve_company(raw):
    """
    (company, error) for an admin-supplied ``company_id``. Blank/None gives (None, None),
    meaning "no company" (a muLearn statement). Only verified, non-deleted companies qualify.
    """
    company_id = (raw or "").strip()
    if not company_id:
        return None, None
    company = Company.objects.select_related("company_user").filter(
        id=company_id, status="verified", deleted_at__isnull=True
    ).first()
    if not company:
        return None, failure("Verified company not found.", 404)
    return company, None


def notify_company(company, statement, actor_id, event):
    """
    Best-effort in-app notification to the company's user; never fails the write.
    ``event`` is "created", "updated", "assigned" or "removed". Skipped when the
    company user is the actor (a company editing its own statement).
    """
    if company is None or company.company_user_id is None or company.company_user_id == actor_id:
        return
    title_text = statement.title
    messages = {
        "created": (
            "Problem statement created for your company",
            f'An admin created the problem statement "{title_text}" on behalf of {company.name}. '
            "It is in Draft; review and publish it.",
        ),
        "updated": (
            "Your company's problem statement was updated",
            f'An admin updated the problem statement "{title_text}".',
        ),
        "assigned": (
            "A problem statement was assigned to your company",
            f'The problem statement "{title_text}" was assigned to {company.name}.',
        ),
        "removed": (
            "A problem statement was moved from your company",
            f'The problem statement "{title_text}" is no longer linked to {company.name}.',
        ),
    }
    title, description = messages[event]
    try:
        from api.notification.notifications_utils import NotificationUtils
        NotificationUtils.insert_notification(
            user=company.company_user, title=title, description=description,
            button=None, url=None, created_by_id=actor_id,
        )
    except Exception:
        logger.exception("Failed to notify company %s for problem statement %s", company.id, statement.id)


def apply_changes(statement_id, data, user_id, on_behalf_of_id=_UNSET, company=_UNSET, result=None):
    """
    Returns an error response, or None on success. ``on_behalf_of_id`` None clears the mention.
    ``company`` (a Company or None) re-links the statement and sets ``source`` to match.
    If a ``result`` dict is passed it receives ``previous_on_behalf_of_id`` and
    ``previous_company_id``, read under the row lock.
    """
    with transaction.atomic():
        statement = ProblemStatement.objects.select_for_update().filter(id=statement_id).first()
        if not statement:
            return not_found()
        if result is not None:
            result["previous_on_behalf_of_id"] = statement.on_behalf_of_id
            result["previous_company_id"] = statement.company_id
        changed = [field for field in EDITABLE_FIELDS if field in data]
        for field in changed:
            setattr(statement, field, data[field])
        if on_behalf_of_id is not _UNSET:
            statement.on_behalf_of_id = on_behalf_of_id
            changed.append("on_behalf_of")
        if company is not _UNSET:
            statement.company = company
            statement.source = (
                ProblemStatement.Source.COMPANY if company else ProblemStatement.Source.MULEARN
            )
            changed.extend(["company", "source"])
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
