"""Shared logic for the company, admin and learner problem statement views."""
from django.db.models import Count
from django.utils import timezone

from db.company import Company
from db.problem_statement import ProblemStatement, ProblemStatementInteraction
from utils.permission import JWTUtils
from utils.response import CustomResponse
from utils.types import RoleType


def failure(message, status_code=400):
    return CustomResponse(general_message=message).get_failure_response(
        status_code=status_code, http_status_code=status_code
    )


def is_admin(request):
    return RoleType.ADMIN.value in JWTUtils.fetch_role(request)


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


def apply_changes(statement, data, user_id):
    for field in ("title", "description", "category", "skills", "deadline"):
        if field in data:
            setattr(statement, field, data[field])
    statement.updated_by_id = user_id
    statement.save()


def publish(statement, user_id):
    if statement.status == ProblemStatement.Status.PUBLISHED:
        return failure("Problem statement is already published.", 409)
    if statement.deadline and statement.deadline <= timezone.now():
        return failure("Cannot publish a problem statement whose deadline has passed.", 409)
    now = timezone.now()
    statement.status = ProblemStatement.Status.PUBLISHED
    statement.published_by_id = user_id
    statement.published_at = now
    statement.updated_by_id = user_id
    statement.save()
    return None


def unpublish(statement, user_id):
    if statement.status != ProblemStatement.Status.PUBLISHED:
        return failure("Only a published problem statement can be unpublished.", 409)
    statement.status = ProblemStatement.Status.UNPUBLISHED
    statement.updated_by_id = user_id
    statement.save()
    return None


def company_scope(request):
    """
    (queryset, company, error) for a company user: only their own company's statements.
    Needs the Company role and the verified company registered by that user;
    co-admins and company mentors are not accepted.
    """
    if RoleType.COMPANY.value not in JWTUtils.fetch_role(request):
        return None, None, failure("You do not have the required role to access this page.", 403)
    user_id = JWTUtils.fetch_user_id(request)
    company = Company.objects.filter(company_user_id=user_id, status="verified").first()
    if not company:
        return None, None, failure("Verified company profile not found or access denied.", 403)
    return statement_queryset().filter(company=company), company, None


def admin_scope(request):
    """(queryset, company, error) for an admin: every statement."""
    if not is_admin(request):
        return None, None, failure("You do not have the required role to access this page.", 403)
    return statement_queryset(), None, None
