"""Helpers shared by the problem statement company, admin and learner views."""
import logging

from django.db import IntegrityError, transaction
from django.db.models import Count
from django.utils import timezone

from db.company import Company
from db.organization import Organization
from db.user import User
from db.problem_statement import ProblemStatement, ProblemStatementInteraction
from utils.response import CustomResponse
from utils.types import OrganizationType

logger = logging.getLogger(__name__)

EDITABLE_FIELDS = ("title", "description", "category", "skills", "deadline")


def failure(message, status_code=400):
    return CustomResponse(general_message=message).get_failure_response(
        status_code=status_code, http_status_code=status_code
    )


def not_found():
    return failure("Problem statement not found.", 404)


def statement_queryset():
    return ProblemStatement.objects.select_related("company", "community", "on_behalf_of")


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


def resolve_community(raw):
    """(community, error) for an admin-supplied ``community_id``; blank/None gives (None, None)."""
    community_id = (raw or "").strip()
    if not community_id:
        return None, None
    community = Organization.objects.filter(
        id=community_id, org_type=OrganizationType.COMMUNITY.value
    ).first()
    if not community:
        return None, failure("Community not found.", 404)
    return community, None


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


def notify_company_after_edit(statement, data, outcome, actor_id, relink_requested):
    """Best-effort notifications to the companies affected by an admin edit; never raises."""
    try:
        previous_id = outcome.get("previous_company_id")
        if relink_requested and "company" in outcome:  # the link actually changed
            if outcome["company"]:
                notify_company(outcome["company"], statement, actor_id, "assigned")
            if previous_id:
                previous = Company.objects.select_related("company_user").filter(id=previous_id).first()
                notify_company(previous, statement, actor_id, "removed")
        elif previous_id and any(f in data for f in EDITABLE_FIELDS):
            owner = Company.objects.select_related("company_user").filter(id=previous_id).first()
            notify_company(owner, statement, actor_id, "updated")
    except Exception:
        logger.exception("Failed to notify companies for problem statement %s", statement.id)


def apply_changes(statement_id, data, user_id, on_behalf_of_id=_UNSET, company_id=_UNSET,
                  community_id=_UNSET, result=None):
    """
    Returns an error response, or None on success. ``on_behalf_of_id`` None clears the mention.
    ``company_id`` / ``community_id`` re-link the statement; None unlinks it. A statement has a
    company OR a community, so setting one clears the other, and ``source`` follows
    (company / community / mulearn). The target is re-checked (verified company, or an
    organization of type Community) and locked inside the transaction, so it can't be
    un-verified or deleted between the check and the write. Linking what it already has is a
    no-op. If a ``result`` dict is passed it receives ``previous_on_behalf_of_id``,
    ``previous_company_id`` (read under the row lock) and, when the company link changed,
    ``company`` (the new Company or None).
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
        if company_id is not _UNSET or community_id is not _UNSET:
            new_company_id = statement.company_id if company_id is _UNSET else (company_id or None)
            new_community_id = statement.community_id if community_id is _UNSET else (community_id or None)
            if new_company_id and company_id is not _UNSET:
                new_community_id = None
            elif new_community_id and community_id is not _UNSET:
                new_company_id = None
            company_changed = str(new_company_id or "") != str(statement.company_id or "")
            community_changed = str(new_community_id or "") != str(statement.community_id or "")
            company = community = None
            if company_changed and new_company_id:
                company = Company.objects.select_for_update().select_related("company_user").filter(
                    id=new_company_id, status="verified", deleted_at__isnull=True
                ).first()
                if not company:
                    return failure("Verified company not found.", 404)
            if community_changed and new_community_id:
                community = Organization.objects.select_for_update().filter(
                    id=new_community_id, org_type=OrganizationType.COMMUNITY.value
                ).first()
                if not community:
                    return failure("Community not found.", 404)
            if company_changed:
                statement.company = company
                changed.append("company")
                if result is not None:
                    result["company"] = company
            if community_changed:
                statement.community = community
                changed.append("community")
            if company_changed or community_changed:
                statement.source = (
                    ProblemStatement.Source.COMPANY if new_company_id
                    else ProblemStatement.Source.COMMUNITY if new_community_id
                    else ProblemStatement.Source.MULEARN
                )
                changed.append("source")
        statement.updated_by_id = user_id
        try:
            statement.save(update_fields=[*changed, "updated_by", "updated_at"])
        except IntegrityError:
            # FK failure: the company/community or the acting user was deleted under us.
            return failure("Company, community or user not found.", 404)
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
