"""
Phase 4 — Audit Writer and Nightly Expiry Task Tests.
Exercises central audit logger, management API audit integrations, and Celery cron task.
"""
import uuid
import datetime
from datetime import timedelta
import jwt

import pytest
from django.utils import timezone
from django.conf import settings
from rest_framework.test import APIClient

from db.problem_statement import (
    ProblemStatement,
    ProblemStatementAuditLog,
)
from db.user import User
from db.company import Company
from api.dashboard.problem_statement.ps_logger import log_ps_action, build_diff
from mu_celery.problem_statement_tasks import close_expired_problem_statements


def make_jwt_token(user_id, roles=None, muid="test-muid"):
    """Generate valid JWT token matching JWTUtils specification."""
    if roles is None:
        roles = ["Admin"]
    expiry_dt = datetime.datetime.now(datetime.timezone.utc) + timedelta(days=1)
    expiry_str = expiry_dt.strftime("%Y-%m-%d %H:%M:%S%z")
    payload = {
        "id": user_id,
        "expiry": expiry_str,
        "roles": roles,
        "muid": muid,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def auth_header(token):
    """Format Bearer token header dict for APIClient."""
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.mark.django_db
class TestAuditLoggerAndCronTask:

    def setup_method(self):
        self.client = APIClient()
        self.user_id = str(uuid.uuid4())
        self.sys_admin_id = settings.SYSTEM_ADMIN_ID

        # Ensure system admin and test user exist in DB
        self.admin_user, _ = User.objects.get_or_create(
            id=self.sys_admin_id,
            defaults={
                'email': 'admin@mulearn.org',
                'full_name': 'System Admin',
                'muid': 'sys-admin-muid',
            }
        )
        self.test_user, _ = User.objects.get_or_create(
            id=self.user_id,
            defaults={
                'email': 'testuser@mulearn.org',
                'full_name': 'Test User',
                'muid': 'test-user-muid',
            }
        )

        self.company = Company.objects.create(
            id=str(uuid.uuid4()),
            name=f"Test Company {uuid.uuid4().hex[:6]}",
            company_user=self.test_user,
            slug=f"company-{uuid.uuid4().hex[:6]}",
            description="Company Description",
            status="verified",
            updated_by=self.user_id,
        )

        self.ps = ProblemStatement.objects.create(
            id=str(uuid.uuid4()),
            title="Initial Title",
            description="Initial Description",
            summary="Initial Summary",
            company=self.company,
            status=ProblemStatement.Status.DRAFT,
            created_by=self.test_user,
            updated_by=self.test_user,
        )

    # =========================================================================
    # PART 1: TEST AUDIT LOGGER (1 - 7)
    # =========================================================================

    def test_1_created_action_creates_audit_row(self):
        log_ps_action(self.ps, ProblemStatementAuditLog.Action.CREATED, self.user_id, actor_role="Admin")
        log_entry = ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.CREATED).first()
        assert log_entry is not None
        assert log_entry.actor_id == self.user_id
        assert log_entry.actor_role == "Admin"

    def test_2_updated_action_creates_audit_row(self):
        log_ps_action(self.ps, ProblemStatementAuditLog.Action.UPDATED, self.user_id, actor_role="Admin", metadata={"changes": {"Title": {"from": "Old", "to": "New"}}})
        log_entry = ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.UPDATED).first()
        assert log_entry is not None
        assert log_entry.metadata["changes"]["Title"]["to"] == "New"

    def test_3_updated_diff_contains_changed_fields(self):
        diff = build_diff(self.ps, {"title": "Brand New Title"})
        assert "Title" in diff
        assert diff["Title"]["from"] == "Initial Title"
        assert diff["Title"]["to"] == "Brand New Title"

        log_ps_action(self.ps, ProblemStatementAuditLog.Action.UPDATED, self.user_id, actor_role="Admin", metadata={"changes": diff})
        log_entry = ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.UPDATED).first()
        assert log_entry.metadata["changes"]["Title"]["to"] == "Brand New Title"

    def test_4_published_action_creates_audit_row(self):
        log_ps_action(self.ps, ProblemStatementAuditLog.Action.PUBLISHED, self.user_id, actor_role="Admin")
        assert ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.PUBLISHED).exists()

    def test_5_closed_action_creates_audit_row(self):
        log_ps_action(self.ps, ProblemStatementAuditLog.Action.CLOSED, self.user_id, actor_role="Admin")
        assert ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.CLOSED).exists()

    def test_6_archived_action_creates_audit_row(self):
        log_ps_action(self.ps, ProblemStatementAuditLog.Action.ARCHIVED, self.user_id, actor_role="Admin")
        assert ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.ARCHIVED).exists()

    def test_7_removed_action_creates_audit_row(self):
        log_ps_action(self.ps, ProblemStatementAuditLog.Action.REMOVED, self.user_id, actor_role="Admin", metadata={"reason": "Testing removal"})
        log_entry = ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.REMOVED).first()
        assert log_entry is not None
        assert log_entry.metadata["reason"] == "Testing removal"

    # =========================================================================
    # PART 2: TEST MANAGEMENT INTEGRATION (8 - 14)
    # =========================================================================

    def test_8_creating_a_problem_statement_produces_exactly_one_created_audit_row(self):
        token = make_jwt_token(self.user_id, roles=["Admin"])
        payload = {
            "title": "API Created PS",
            "description": "API Created Description",
            "summary": "API Created Summary",
        }
        res = self.client.post("/api/v1/dashboard/problem-statements/manage/", payload, format="json", **auth_header(token))
        assert res.status_code == 200
        new_ps_id = res.data["response"]["id"]
        logs = ProblemStatementAuditLog.objects.filter(problem_statement_id=new_ps_id, action=ProblemStatementAuditLog.Action.CREATED)
        assert logs.count() == 1

    def test_9_updating_a_problem_statement_produces_updated_audit_row_with_changes(self):
        token = make_jwt_token(self.user_id, roles=["Admin"])
        payload = {
            "title": "Updated Title via API",
            "description": "Initial Description",
            "summary": "Initial Summary",
        }
        res = self.client.put(f"/api/v1/dashboard/problem-statements/manage/{self.ps.id}/", payload, format="json", **auth_header(token))
        assert res.status_code == 200
        logs = ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.UPDATED)
        assert logs.count() == 1
        assert logs.first().metadata["changes"]["Title"]["to"] == "Updated Title via API"

    def test_10_publishing_produces_published_audit_row(self):
        token = make_jwt_token(self.user_id, roles=["Admin"])
        res = self.client.post(f"/api/v1/dashboard/problem-statements/manage/{self.ps.id}/publish/", **auth_header(token))
        assert res.status_code == 200
        logs = ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.PUBLISHED)
        assert logs.count() == 1

    def test_11_closing_produces_closed_audit_row(self):
        self.ps.status = ProblemStatement.Status.PUBLISHED
        self.ps.published_at = timezone.now()
        self.ps.save()

        token = make_jwt_token(self.user_id, roles=["Admin"])
        res = self.client.post(f"/api/v1/dashboard/problem-statements/manage/{self.ps.id}/close/", **auth_header(token))
        assert res.status_code == 200
        logs = ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.CLOSED)
        assert logs.count() == 1

    def test_12_archiving_produces_archived_audit_row(self):
        self.ps.status = ProblemStatement.Status.PUBLISHED
        self.ps.published_at = timezone.now()
        self.ps.save()

        token = make_jwt_token(self.user_id, roles=["Admin"])
        res = self.client.post(f"/api/v1/dashboard/problem-statements/manage/{self.ps.id}/archive/", **auth_header(token))
        assert res.status_code == 200
        logs = ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.ARCHIVED)
        assert logs.count() == 1

    def test_13_removing_produces_exactly_one_removed_audit_row(self):
        token = make_jwt_token(self.user_id, roles=["Admin"])
        res = self.client.post(
            f"/api/v1/dashboard/problem-statements/manage/{self.ps.id}/remove/",
            {"reason": "Deprecation removal"},
            format="json",
            **auth_header(token)
        )
        assert res.status_code == 200
        logs = ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.REMOVED)
        assert logs.count() == 1
        assert logs.first().metadata["reason"] == "Deprecation removal"

    def test_14_delete_removal_does_not_produce_duplicate_removed_rows(self):
        token = make_jwt_token(self.user_id, roles=["Admin"])
        res = self.client.delete(f"/api/v1/dashboard/problem-statements/manage/{self.ps.id}/", **auth_header(token))
        assert res.status_code == 200
        logs = ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.REMOVED)
        assert logs.count() == 1

    # =========================================================================
    # PART 3: TEST NIGHTLY TASK (15 - 28)
    # =========================================================================

    def test_15_published_ps_with_past_deadline_is_closed(self):
        self.ps.status = ProblemStatement.Status.PUBLISHED
        self.ps.deadline = timezone.now() - timedelta(days=1)
        self.ps.save()

        close_expired_problem_statements()
        self.ps.refresh_from_db()
        assert self.ps.status == ProblemStatement.Status.CLOSED

    def test_16_closed_at_is_set(self):
        self.ps.status = ProblemStatement.Status.PUBLISHED
        self.ps.deadline = timezone.now() - timedelta(hours=2)
        self.ps.save()

        close_expired_problem_statements()
        self.ps.refresh_from_db()
        assert self.ps.closed_at is not None

    def test_17_updated_by_remains_unchanged_on_model(self):
        original_updated_by = self.ps.updated_by_id
        self.ps.status = ProblemStatement.Status.PUBLISHED
        self.ps.deadline = timezone.now() - timedelta(hours=2)
        self.ps.save()

        close_expired_problem_statements()
        self.ps.refresh_from_db()
        assert self.ps.updated_by_id == original_updated_by

    def test_18_closed_audit_row_is_created(self):
        self.ps.status = ProblemStatement.Status.PUBLISHED
        self.ps.deadline = timezone.now() - timedelta(hours=2)
        self.ps.save()

        close_expired_problem_statements()
        assert ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.CLOSED).exists()

    def test_19_audit_actor_id_is_system_admin_id(self):
        self.ps.status = ProblemStatement.Status.PUBLISHED
        self.ps.deadline = timezone.now() - timedelta(hours=2)
        self.ps.save()

        close_expired_problem_statements()
        log_entry = ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.CLOSED).first()
        assert str(log_entry.actor_id) == str(self.sys_admin_id)

    def test_20_audit_actor_role_is_system_cron(self):
        self.ps.status = ProblemStatement.Status.PUBLISHED
        self.ps.deadline = timezone.now() - timedelta(hours=2)
        self.ps.save()

        close_expired_problem_statements()
        log_entry = ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.CLOSED).first()
        assert log_entry.actor_role == "System/Cron"

    def test_21_future_deadline_remains_published(self):
        self.ps.status = ProblemStatement.Status.PUBLISHED
        self.ps.deadline = timezone.now() + timedelta(days=5)
        self.ps.save()

        close_expired_problem_statements()
        self.ps.refresh_from_db()
        assert self.ps.status == ProblemStatement.Status.PUBLISHED
        assert not ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.CLOSED).exists()

    def test_22_null_deadline_remains_unchanged(self):
        self.ps.status = ProblemStatement.Status.PUBLISHED
        self.ps.deadline = None
        self.ps.save()

        close_expired_problem_statements()
        self.ps.refresh_from_db()
        assert self.ps.status == ProblemStatement.Status.PUBLISHED

    def test_23_draft_remains_unchanged(self):
        self.ps.status = ProblemStatement.Status.DRAFT
        self.ps.deadline = timezone.now() - timedelta(days=2)
        self.ps.save()

        close_expired_problem_statements()
        self.ps.refresh_from_db()
        assert self.ps.status == ProblemStatement.Status.DRAFT

    def test_24_already_closed_remains_unchanged(self):
        self.ps.status = ProblemStatement.Status.CLOSED
        self.ps.deadline = timezone.now() - timedelta(days=2)
        self.ps.save()

        close_expired_problem_statements()
        self.ps.refresh_from_db()
        assert self.ps.status == ProblemStatement.Status.CLOSED
        assert not ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.CLOSED).exists()

    def test_25_archived_remains_unchanged(self):
        self.ps.status = ProblemStatement.Status.ARCHIVED
        self.ps.deadline = timezone.now() - timedelta(days=2)
        self.ps.save()

        close_expired_problem_statements()
        self.ps.refresh_from_db()
        assert self.ps.status == ProblemStatement.Status.ARCHIVED

    def test_26_removed_remains_unchanged(self):
        self.ps.status = ProblemStatement.Status.REMOVED
        self.ps.deadline = timezone.now() - timedelta(days=2)
        self.ps.save()

        close_expired_problem_statements()
        self.ps.refresh_from_db()
        assert self.ps.status == ProblemStatement.Status.REMOVED

    def test_27_deleted_published_record_remains_unchanged(self):
        self.ps.status = ProblemStatement.Status.PUBLISHED
        self.ps.deadline = timezone.now() - timedelta(days=2)
        self.ps.deleted_at = timezone.now()
        self.ps.save()

        close_expired_problem_statements()
        self.ps.refresh_from_db()
        assert self.ps.status == ProblemStatement.Status.PUBLISHED

    def test_28_running_task_twice_does_not_create_duplicate_closed_audit_rows(self):
        self.ps.status = ProblemStatement.Status.PUBLISHED
        self.ps.deadline = timezone.now() - timedelta(days=1)
        self.ps.save()

        close_expired_problem_statements()
        close_expired_problem_statements()

        logs = ProblemStatementAuditLog.objects.filter(problem_statement=self.ps, action=ProblemStatementAuditLog.Action.CLOSED)
        assert logs.count() == 1
