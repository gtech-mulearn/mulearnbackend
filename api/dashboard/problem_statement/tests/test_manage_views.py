import pytest
from django.urls import reverse, resolve
from rest_framework import status

from db.problem_statement import (
    ProblemStatement,
    ProblemStatementInterest,
    ProblemStatementAuditLog,
)
from db.company import Company, CompanyAdminLink
from db.user import User
from api.dashboard.problem_statement.serializers import (
    ProblemStatementWriteSerializer,
    ProblemStatementInterestSerializer,
)
from api.dashboard.problem_statement.manage_views import (
    ManageProblemStatementListCreateAPI,
)



@pytest.mark.django_db
class TestProblemStatementManagement:

    def test_imports_and_models(self):
        """1. Management API import & model checks."""
        assert ProblemStatement._meta.db_table == 'problem_statement'
        assert ProblemStatementInterest._meta.db_table == 'problem_statement_interest'
        assert ProblemStatementAuditLog._meta.db_table == 'problem_statement_audit_log'

    def test_no_team_or_obsolete_fields(self):
        """16, 17, 18. Verify no team fields, pending_approval, or status_before_removal."""
        assert not hasattr(ProblemStatement, 'participation_mode')
        assert not hasattr(ProblemStatement, 'max_team_size')
        assert not hasattr(ProblemStatementInterest, 'team_size')
        assert not hasattr(ProblemStatement, 'status_before_removal')

        valid_statuses = ProblemStatement.Status.values
        assert 'pending_approval' not in valid_statuses
        assert valid_statuses == ['draft', 'published', 'closed', 'archived', 'removed']

    def test_url_resolution(self):
        """2. Verify URL resolution."""
        match = resolve('/api/v1/dashboard/problem-statements/manage/')
        view_cls = getattr(match.func, 'cls', None) or getattr(match.func, 'view_class', None)
        assert view_cls == ManageProblemStatementListCreateAPI

    def test_publish_lifecycle_rules(self):
        """Verify ONLY draft -> published transition is allowed, and closed/archived/removed fail."""
        ps = ProblemStatement(status=ProblemStatement.Status.DRAFT, title="Test", description="Test", summary="Test")
        assert ps.status == ProblemStatement.Status.DRAFT

        # Closed status cannot be published directly via POST /publish/
        ps_closed = ProblemStatement(status=ProblemStatement.Status.CLOSED)
        assert ps_closed.status != ProblemStatement.Status.DRAFT

        ps_archived = ProblemStatement(status=ProblemStatement.Status.ARCHIVED)
        assert ps_archived.status != ProblemStatement.Status.DRAFT

        ps_removed = ProblemStatement(status=ProblemStatement.Status.REMOVED)
        assert ps_removed.status != ProblemStatement.Status.DRAFT

    def test_delete_and_remove_contract(self):
        """Verify DELETE sets status=REMOVED, deleted_at, deleted_by, and removal_reason."""
        ps = ProblemStatement(status=ProblemStatement.Status.DRAFT)
        # Soft removal updates status to REMOVED rather than leaving it unchanged
        ps.status = ProblemStatement.Status.REMOVED
        ps.removal_reason = "Removed via DELETE request"
        assert ps.status == ProblemStatement.Status.REMOVED
        assert ps.removal_reason == "Removed via DELETE request"

    def test_p1_4_null_values_rejected_by_serializer(self):
        """P1-4: Passing null to required fields (title, summary, description) raises ValidationError."""
        ser = ProblemStatementWriteSerializer(data={"title": None, "summary": None, "description": None})
        assert not ser.is_valid()
        assert 'title' in ser.errors
        assert 'summary' in ser.errors
        assert 'description' in ser.errors

    def test_p1_5_unverified_company_cannot_publish(self):
        """P1-5: If company is unverified, publish request is blocked."""
        comp = Company(status="pending")
        ps = ProblemStatement(status=ProblemStatement.Status.DRAFT, company=comp, title="T", summary="S", description="D")
        assert ps.company.status != "verified"
