"""
Manage Problem Statement API views.
Company owner / co-admin delegate or System Admin access required.
"""
import uuid
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework import status
from drf_spectacular.utils import extend_schema

from db.problem_statement import (
    ProblemStatement,
    ProblemStatementInterest,
    ProblemStatementAuditLog,
)
from db.company import Company, CompanyAdminLink
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils
from utils.types import RoleType

from .serializers import (
    ProblemStatementWriteSerializer,
    ProblemStatementDetailSerializer,
    ProblemStatementListItemSerializer,
    ProblemStatementAuditLogSerializer,
)
from .ps_logger import log_ps_action, build_diff
from api.dashboard.company.company_views import is_company_owner_or_admin


def _get_actor_role(roles):
    if isinstance(roles, list) and len(roles) > 0:
        return roles[0]
    if isinstance(roles, str):
        return roles
    return None


def _get_user_companies(user_id):
    """
    Returns a QuerySet of verified Company objects where user_id is the registrant
    (company_user_id) or an accepted Co-Admin delegate (CompanyAdminLink).
    """
    return Company.objects.filter(
        Q(company_user_id=user_id) | Q(
            admin_links__user_id=user_id,
            admin_links__status=CompanyAdminLink.Status.ACCEPTED,
        ),
        status="verified",
    ).distinct()


def _can_manage_problem_statement(user_id, roles, problem_statement):
    """True if user is a System Admin or authorized verified Company owner/co-admin."""
    if RoleType.ADMIN.value in roles:
        return True
    if not problem_statement or not problem_statement.company:
        return False
    if problem_statement.company.status != "verified":
        return False
    return is_company_owner_or_admin(user_id, problem_statement.company)


class ManageProblemStatementListCreateAPI(APIView):
    """
    GET  /problem-statements/manage/   → list problem statements manageable by caller
    POST /problem-statements/manage/   → create a new problem statement (draft)
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Problem Statement'],
        description="Retrieve a paginated list of problem statements manageable by the caller (Company owner/delegate or Admin).",
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        is_admin = RoleType.ADMIN.value in roles

        if is_admin:
            queryset = ProblemStatement.objects.filter(deleted_at__isnull=True)
        else:
            companies = _get_user_companies(user_id)
            if not companies.exists():
                return CustomResponse(
                    general_message="Verified company profile not found."
                ).get_failure_response(status_code=403, http_status_code=status.HTTP_403_FORBIDDEN)
            queryset = ProblemStatement.objects.filter(
                company__in=companies, deleted_at__isnull=True
            )

        if status_filter := request.query_params.get('status'):
            queryset = queryset.filter(status=status_filter)

        paginated = CommonUtils.get_paginated_queryset(
            queryset.select_related('company', 'created_by', 'updated_by'),
            request,
            search_fields=['title', 'summary', 'description'],
            sort_fields={'created_at': 'created_at', 'title': 'title', 'deadline': 'deadline'},
        )

        serializer = ProblemStatementListItemSerializer(
            paginated['queryset'], many=True,
            context={'user_id': user_id, 'request': request},
        )
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )

    @extend_schema(
        tags=['Dashboard - Problem Statement'],
        description="Create a new draft problem statement for an authorized company.",
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        is_admin = RoleType.ADMIN.value in roles

        user_companies = _get_user_companies(user_id)
        target_company_id = request.data.get('company_id')

        company = None
        if target_company_id:
            if is_admin:
                company = Company.objects.filter(id=target_company_id, status="verified").first()
                if not company:
                    return CustomResponse(
                        general_message="Target verified company not found."
                    ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)
            else:
                company = user_companies.filter(id=target_company_id).first()
                if not company:
                    return CustomResponse(
                        general_message="You are not authorized to create problem statements for this company."
                    ).get_failure_response(status_code=403, http_status_code=status.HTTP_403_FORBIDDEN)
        else:
            if is_admin:
                return CustomResponse(
                    general_message="Target verified company_id is required for admin creation."
                ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)
            company = user_companies.first()
            if not company:
                return CustomResponse(
                    general_message="Verified company profile not found."
                ).get_failure_response(status_code=403, http_status_code=status.HTTP_403_FORBIDDEN)

        serializer = ProblemStatementWriteSerializer(
            data=request.data,
            context={'user_id': user_id},
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            ps = serializer.save(
                id=str(uuid.uuid4()),
                slug=serializer._generate_unique_slug(serializer.validated_data['title']),
                company=company,
                status=ProblemStatement.Status.DRAFT,
                created_by_id=user_id,
                updated_by_id=user_id,
            )
            log_ps_action(
                problem_statement=ps,
                action=ProblemStatementAuditLog.Action.CREATED,
                actor_id=user_id,
                actor_role=_get_actor_role(roles),
            )

        return CustomResponse(
            general_message="Problem Statement created successfully.",
            response=ProblemStatementDetailSerializer(
                ps, context={'user_id': user_id, 'request': request}
            ).data,
        ).get_success_response()


class ManageProblemStatementDetailAPI(APIView):
    """
    GET    /problem-statements/manage/<ps_id>/ → management detail view + edit history
    PUT    /problem-statements/manage/<ps_id>/ → full update
    PATCH  /problem-statements/manage/<ps_id>/ → partial update
    DELETE /problem-statements/manage/<ps_id>/ → soft delete
    """
    authentication_classes = [CustomizePermission]

    def _get_managed_ps(self, request, ps_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        ps = ProblemStatement.objects.filter(id=ps_id, deleted_at__isnull=True).select_related('company').first()
        if not ps:
            return None, None, None, 'Problem Statement not found.', 404, status.HTTP_404_NOT_FOUND
        if not _can_manage_problem_statement(user_id, roles, ps):
            return None, None, None, 'You do not have permission to manage this Problem Statement.', 403, status.HTTP_403_FORBIDDEN
        return ps, user_id, roles, None, None, None

    @extend_schema(
        tags=['Dashboard - Problem Statement'],
        description="Retrieve full management details and audit history for a specific problem statement.",
    )
    def get(self, request, ps_id):
        ps, user_id, _, error, code, http_code = self._get_managed_ps(request, ps_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response(status_code=code, http_status_code=http_code)

        logs = ProblemStatementAuditLog.objects.filter(problem_statement=ps).order_by('-created_at')
        detail_data = ProblemStatementDetailSerializer(
            ps, context={'user_id': user_id, 'request': request}
        ).data
        detail_data['edit_history'] = ProblemStatementAuditLogSerializer(logs, many=True).data

        return CustomResponse(
            general_message="Problem Statement detail retrieved.",
            response=detail_data,
        ).get_success_response()

    @extend_schema(
        tags=['Dashboard - Problem Statement'],
        description="Full update of an existing problem statement.",
    )
    def put(self, request, ps_id):
        return self._update(request, ps_id, partial=False)

    @extend_schema(
        tags=['Dashboard - Problem Statement'],
        description="Partial update of an existing problem statement.",
    )
    def patch(self, request, ps_id):
        return self._update(request, ps_id, partial=True)

    def _update(self, request, ps_id, partial=False):
        ps, user_id, _, error, code, http_code = self._get_managed_ps(request, ps_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response(status_code=code, http_status_code=http_code)

        if ps.status == ProblemStatement.Status.REMOVED:
            return CustomResponse(
                general_message="Removed Problem Statements cannot be edited."
            ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

        serializer = ProblemStatementWriteSerializer(
            ps, data=request.data, partial=partial, context={'user_id': user_id}
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

        roles = JWTUtils.fetch_role(request)
        diff = build_diff(ps, serializer.validated_data)

        with transaction.atomic():
            ps = serializer.save(updated_by_id=user_id)
            if diff:
                log_ps_action(
                    problem_statement=ps,
                    action=ProblemStatementAuditLog.Action.UPDATED,
                    actor_id=user_id,
                    actor_role=_get_actor_role(roles),
                    metadata={'changes': diff},
                )

        return CustomResponse(
            general_message="Problem Statement updated successfully.",
            response=ProblemStatementDetailSerializer(
                ps, context={'user_id': user_id, 'request': request}
            ).data,
        ).get_success_response()

    @extend_schema(
        tags=['Dashboard - Problem Statement'],
        description="Soft delete a problem statement with a removal reason.",
    )
    def delete(self, request, ps_id):
        ps, user_id, roles, error, code, http_code = self._get_managed_ps(request, ps_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response(status_code=code, http_status_code=http_code)

        reason = (request.data.get('reason') or request.query_params.get('reason') or 'Removed via DELETE request').strip()

        now = timezone.now()
        with transaction.atomic():
            ps.status = ProblemStatement.Status.REMOVED
            ps.removal_reason = reason
            ps.deleted_at = now
            ps.deleted_by_id = user_id
            ps.updated_by_id = user_id
            ps.save(update_fields=['status', 'removal_reason', 'deleted_at', 'deleted_by', 'updated_by', 'updated_at'])
            log_ps_action(
                problem_statement=ps,
                action=ProblemStatementAuditLog.Action.REMOVED,
                actor_id=user_id,
                actor_role=_get_actor_role(roles),
                metadata={'reason': reason},
            )

        return CustomResponse(
            general_message="Problem Statement removed successfully.",
            response={'id': ps.id, 'status': ProblemStatement.Status.REMOVED, 'removal_reason': reason, 'deleted_at': now.isoformat()},
        ).get_success_response()


class ManageProblemStatementPublishAPI(APIView):
    """POST /problem-statements/manage/<ps_id>/publish/ → transition draft to published."""
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Problem Statement'],
        description="Publish a draft problem statement. Requires verified company status.",
    )
    def post(self, request, ps_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        is_admin = RoleType.ADMIN.value in roles

        ps = ProblemStatement.objects.filter(id=ps_id, deleted_at__isnull=True).select_related('company').first()
        if not ps:
            return CustomResponse(general_message='Problem Statement not found.').get_failure_response(status_code=404, http_status_code=status.HTTP_404_NOT_FOUND)
        if not _can_manage_problem_statement(user_id, roles, ps):
            return CustomResponse(general_message='You do not have permission to manage this Problem Statement.').get_failure_response(status_code=403, http_status_code=status.HTTP_403_FORBIDDEN)

        if not is_admin and (not ps.company or ps.company.status != "verified"):
            return CustomResponse(
                general_message="Company must be currently verified to publish Problem Statements."
            ).get_failure_response(status_code=403, http_status_code=status.HTTP_403_FORBIDDEN)

        if ps.status != ProblemStatement.Status.DRAFT:
            return CustomResponse(
                general_message=f'Only draft problem statements can be published (current: {ps.status}).'
            ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

        missing = [f for f in ['title', 'description', 'summary'] if not getattr(ps, f, None)]
        if missing:
            return CustomResponse(
                general_message=f'Cannot publish: missing required fields: {", ".join(missing)}.'
            ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        with transaction.atomic():
            ps.status = ProblemStatement.Status.PUBLISHED
            ps.published_at = now
            ps.updated_by_id = user_id
            ps.save(update_fields=['status', 'published_at', 'updated_by', 'updated_at'])
            log_ps_action(
                problem_statement=ps,
                action=ProblemStatementAuditLog.Action.PUBLISHED,
                actor_id=user_id,
                actor_role=_get_actor_role(roles),
            )

        return CustomResponse(
            general_message="Problem Statement published successfully.",
            response={'id': ps.id, 'status': ProblemStatement.Status.PUBLISHED, 'published_at': now.isoformat()},
        ).get_success_response()


class ManageProblemStatementCloseAPI(APIView):
    """POST /problem-statements/manage/<ps_id>/close/ → transition published to closed."""
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Problem Statement'],
        description="Transition a published problem statement to closed.",
    )
    def post(self, request, ps_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        ps = ProblemStatement.objects.filter(id=ps_id, deleted_at__isnull=True).select_related('company').first()
        if not ps:
            return CustomResponse(general_message='Problem Statement not found.').get_failure_response(status_code=404, http_status_code=status.HTTP_404_NOT_FOUND)
        if not _can_manage_problem_statement(user_id, roles, ps):
            return CustomResponse(general_message='You do not have permission to manage this Problem Statement.').get_failure_response(status_code=403, http_status_code=status.HTTP_403_FORBIDDEN)

        if ps.status != ProblemStatement.Status.PUBLISHED:
            return CustomResponse(
                general_message=f'Only published problem statements can be closed (current: {ps.status}).'
            ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        with transaction.atomic():
            ps.status = ProblemStatement.Status.CLOSED
            ps.closed_at = now
            ps.updated_by_id = user_id
            ps.save(update_fields=['status', 'closed_at', 'updated_by', 'updated_at'])
            log_ps_action(
                problem_statement=ps,
                action=ProblemStatementAuditLog.Action.CLOSED,
                actor_id=user_id,
                actor_role=_get_actor_role(roles),
            )

        return CustomResponse(
            general_message="Problem Statement closed successfully.",
            response={'id': ps.id, 'status': ProblemStatement.Status.CLOSED, 'closed_at': now.isoformat()},
        ).get_success_response()


class ManageProblemStatementArchiveAPI(APIView):
    """POST /problem-statements/manage/<ps_id>/archive/ → transition published/closed to archived."""
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Problem Statement'],
        description="Transition a published or closed problem statement to archived.",
    )
    def post(self, request, ps_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        ps = ProblemStatement.objects.filter(id=ps_id, deleted_at__isnull=True).select_related('company').first()
        if not ps:
            return CustomResponse(general_message='Problem Statement not found.').get_failure_response(status_code=404, http_status_code=status.HTTP_404_NOT_FOUND)
        if not _can_manage_problem_statement(user_id, roles, ps):
            return CustomResponse(general_message='You do not have permission to manage this Problem Statement.').get_failure_response(status_code=403, http_status_code=status.HTTP_403_FORBIDDEN)

        if ps.status not in (ProblemStatement.Status.PUBLISHED, ProblemStatement.Status.CLOSED):
            return CustomResponse(
                general_message=f'Only published or closed problem statements can be archived (current: {ps.status}).'
            ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        with transaction.atomic():
            ps.status = ProblemStatement.Status.ARCHIVED
            ps.archived_at = now
            ps.updated_by_id = user_id
            ps.save(update_fields=['status', 'archived_at', 'updated_by', 'updated_at'])
            log_ps_action(
                problem_statement=ps,
                action=ProblemStatementAuditLog.Action.ARCHIVED,
                actor_id=user_id,
                actor_role=_get_actor_role(roles),
            )

        return CustomResponse(
            general_message="Problem Statement archived successfully.",
            response={'id': ps.id, 'status': ProblemStatement.Status.ARCHIVED, 'archived_at': now.isoformat()},
        ).get_success_response()


class ManageProblemStatementRemoveAPI(APIView):
    """POST /problem-statements/manage/<ps_id>/remove/ → transition any state to removed with reason."""
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Problem Statement'],
        description="Soft delete/remove a problem statement with a mandatory removal reason.",
    )
    def post(self, request, ps_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        ps = ProblemStatement.objects.filter(id=ps_id, deleted_at__isnull=True).select_related('company').first()
        if not ps:
            return CustomResponse(general_message='Problem Statement not found.').get_failure_response(status_code=404, http_status_code=status.HTTP_404_NOT_FOUND)
        if not _can_manage_problem_statement(user_id, roles, ps):
            return CustomResponse(general_message='You do not have permission to manage this Problem Statement.').get_failure_response(status_code=403, http_status_code=status.HTTP_403_FORBIDDEN)

        reason = (request.data.get('reason') or '').strip()
        if not reason:
            return CustomResponse(general_message='A removal reason is required.').get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        with transaction.atomic():
            ps.status = ProblemStatement.Status.REMOVED
            ps.removal_reason = reason
            ps.deleted_at = now
            ps.deleted_by_id = user_id
            ps.updated_by_id = user_id
            ps.save(update_fields=['status', 'removal_reason', 'deleted_at', 'deleted_by', 'updated_by', 'updated_at'])
            log_ps_action(
                problem_statement=ps,
                action=ProblemStatementAuditLog.Action.REMOVED,
                actor_id=user_id,
                actor_role=_get_actor_role(roles),
                metadata={'reason': reason},
            )

        return CustomResponse(
            general_message="Problem Statement removed successfully.",
            response={'id': ps.id, 'status': ProblemStatement.Status.REMOVED, 'removal_reason': reason},
        ).get_success_response()
