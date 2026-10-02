"""
Comprehensive API test suite for Phase 3 Learner + Public Problem Statement APIs.
Exercises all 40 functional, security, lifecycle, and counter requirements via APIClient.
"""
import uuid
import datetime
from datetime import timedelta
import jwt

import pytest
from django.utils import timezone
from django.conf import settings
from django.urls import resolve
from rest_framework.test import APIClient
from rest_framework import status

from db.problem_statement import (
    ProblemStatement,
    ProblemStatementInterest,
)
from db.user import User
from db.company import Company
from api.dashboard.problem_statement.public_views import (
    ProblemStatementListAPI,
    ProblemStatementDetailAPI,
    ProblemStatementInterestAPI,
    LearnerMyInterestsAPI,
)


def make_jwt_token(user_id, roles=None, muid="test-muid"):
    """Generate valid JWT token matching JWTUtils specification."""
    if roles is None:
        roles = ["Student"]
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
class TestProblemStatementPublicAndLearnerAPIs:

    def setup_method(self):
        self.client = APIClient()
        self.user_a_id = str(uuid.uuid4())
        self.user_b_id = str(uuid.uuid4())
        self.sys_admin_id = settings.SYSTEM_ADMIN_ID

        # Ensure base users exist in DB if DB checks are active
        self.user_a, _ = User.objects.get_or_create(
            muid='user_a_muid',
            defaults={
                'id': self.user_a_id,
                'email': 'user_a@example.com',
                'full_name': 'Learner A',
                'created_at': timezone.now(),
            },
        )
        self.user_a_id = self.user_a.id

        self.user_b, _ = User.objects.get_or_create(
            muid='user_b_muid',
            defaults={
                'id': self.user_b_id,
                'email': 'user_b@example.com',
                'full_name': 'Learner B',
                'created_at': timezone.now(),
            },
        )
        self.user_b_id = self.user_b.id

        self.sys_admin, _ = User.objects.get_or_create(
            id=self.sys_admin_id,
            defaults={
                'email': 'admin@example.com',
                'muid': 'admin_muid',
                'full_name': 'System Admin',
                'created_at': timezone.now(),
            },
        )


        self.company, _ = Company.objects.get_or_create(
            company_user=self.sys_admin,
            defaults={
                'id': str(uuid.uuid4()),
                'name': 'Test Tech Corp',
                'slug': 'test-tech-corp',
                'description': 'Test company description',
                'status': 'verified',
            },
        )



        self.token_a = make_jwt_token(self.user_a_id, muid="user_a_muid")
        self.token_b = make_jwt_token(self.user_b_id, muid="user_b_muid")

    def _create_ps(self, title="Test PS", ps_status=ProblemStatement.Status.PUBLISHED, deadline=None, deleted=False, categories=None, skills=None):
        now = timezone.now()
        ps = ProblemStatement.objects.create(
            id=str(uuid.uuid4()),
            title=title,
            slug=f"ps-{uuid.uuid4().hex[:8]}",
            summary="Summary text",
            description="Detailed description text",
            company=self.company,
            status=ps_status,
            deadline=deadline,
            categories=categories,
            skills=skills,
            created_by=self.sys_admin,
            updated_by=self.sys_admin,
            deleted_at=now if deleted else None,
            deleted_by=self.sys_admin if deleted else None,
        )
        return ps

    # ─────────────────────────────────────────────────────────────
    # Structural & Routing Verification
    # ─────────────────────────────────────────────────────────────

    def test_url_resolutions(self):
        """Verify URL mappings for Phase 3 endpoints."""
        m_list = resolve('/api/v1/dashboard/problem-statements/')
        assert (getattr(m_list.func, 'cls', None) or getattr(m_list.func, 'view_class', None)) == ProblemStatementListAPI

        m_my_interests = resolve('/api/v1/dashboard/problem-statements/my-interests/')
        assert (getattr(m_my_interests.func, 'cls', None) or getattr(m_my_interests.func, 'view_class', None)) == LearnerMyInterestsAPI

        m_detail = resolve('/api/v1/dashboard/problem-statements/test-id/')
        assert (getattr(m_detail.func, 'cls', None) or getattr(m_detail.func, 'view_class', None)) == ProblemStatementDetailAPI

        m_interest = resolve('/api/v1/dashboard/problem-statements/test-id/interest/')
        assert (getattr(m_interest.func, 'cls', None) or getattr(m_interest.func, 'view_class', None)) == ProblemStatementInterestAPI

    # ─────────────────────────────────────────────────────────────
    # 1. PUBLIC LIST TESTS (Req 1 - 6)
    # ─────────────────────────────────────────────────────────────

    def test_req_01_to_06_public_list_filtering(self):
        """Req 1-6: Anonymous list succeeds; only published non-deleted PS appear."""
        ps_pub = self._create_ps(title="Published PS", ps_status=ProblemStatement.Status.PUBLISHED)
        ps_draft = self._create_ps(title="Draft PS", ps_status=ProblemStatement.Status.DRAFT)
        ps_closed = self._create_ps(title="Closed PS", ps_status=ProblemStatement.Status.CLOSED)
        ps_archived = self._create_ps(title="Archived PS", ps_status=ProblemStatement.Status.ARCHIVED)
        ps_removed = self._create_ps(title="Removed PS", ps_status=ProblemStatement.Status.REMOVED)
        ps_deleted = self._create_ps(title="Deleted PS", ps_status=ProblemStatement.Status.PUBLISHED, deleted=True)

        resp = self.client.get('/api/v1/dashboard/problem-statements/?perPage=100')
        assert resp.status_code == status.HTTP_200_OK



        data = resp.json().get('response', {}).get('data', [])
        returned_ids = [item['id'] for item in data]

        assert ps_pub.id in returned_ids  # Req 1 & 2: Anonymous GET succeeds, Published appears
        assert ps_draft.id not in returned_ids  # Req 3: Draft does not appear
        assert ps_closed.id not in returned_ids  # Req 4: Closed does not appear
        assert ps_archived.id not in returned_ids  # Req 5: Archived does not appear
        assert ps_removed.id not in returned_ids  # Req 6: Removed does not appear
        assert ps_deleted.id not in returned_ids  # Soft-deleted does not appear

    # ─────────────────────────────────────────────────────────────
    # 2. PUBLIC DETAIL TESTS (Req 7 - 10)
    # ─────────────────────────────────────────────────────────────

    def test_req_07_to_10_public_detail_and_view_count(self):
        """Req 7-10: Detail succeeds for published; non-published returns 404; view_count increments."""
        ps_pub = self._create_ps(title="Pub Detail PS", ps_status=ProblemStatement.Status.PUBLISHED)
        initial_views = ps_pub.view_count

        # Req 7: Anonymous user can retrieve published PS
        resp = self.client.get(f'/api/v1/dashboard/problem-statements/{ps_pub.id}/')
        assert resp.status_code == status.HTTP_200_OK

        # Req 9: View count increments after successful detail request
        ps_pub.refresh_from_db()
        assert ps_pub.view_count == initial_views + 1

        # Req 8 & 10: Non-published returns 404 and does not increment view count
        ps_draft = self._create_ps(title="Draft Detail PS", ps_status=ProblemStatement.Status.DRAFT)
        draft_views = ps_draft.view_count

        resp_draft = self.client.get(f'/api/v1/dashboard/problem-statements/{ps_draft.id}/')
        assert resp_draft.status_code == status.HTTP_404_NOT_FOUND

        ps_draft.refresh_from_db()
        assert ps_draft.view_count == draft_views  # Req 10: View count not incremented

    # ─────────────────────────────────────────────────────────────
    # 3. CREATE INTEREST TESTS (Req 11 - 20)
    # ─────────────────────────────────────────────────────────────

    def test_req_11_to_20_create_interest_rules(self):
        """Req 11-20: Create interest permissions, lifecycle restrictions, and deadline checks."""
        ps_pub = self._create_ps(title="Interest PS", ps_status=ProblemStatement.Status.PUBLISHED)

        # Req 12 & 13: Anonymous or invalid token cannot create interest
        resp_anon = self.client.post(f'/api/v1/dashboard/problem-statements/{ps_pub.id}/interest/')
        assert resp_anon.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

        resp_invalid = self.client.post(
            f'/api/v1/dashboard/problem-statements/{ps_pub.id}/interest/',
            **{"HTTP_AUTHORIZATION": "Bearer invalid.jwt.token"}
        )
        assert resp_invalid.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

        # Req 11 & 14: Authenticated learner can create interest for published PS
        payload = {"note": "Super excited!", "work_link": "https://github.com/test/repo"}
        resp = self.client.post(
            f'/api/v1/dashboard/problem-statements/{ps_pub.id}/interest/',
            data=payload,
            format='json',
            **auth_header(self.token_a)
        )
        assert resp.status_code == status.HTTP_200_OK

        interest = ProblemStatementInterest.objects.filter(problem_statement=ps_pub, user=self.user_a).first()
        assert interest is not None
        assert interest.status == ProblemStatementInterest.Status.INTERESTED
        assert interest.user_id == self.user_a_id

        # Req 15: Draft PS rejects interest
        ps_draft = self._create_ps(ps_status=ProblemStatement.Status.DRAFT)
        r_draft = self.client.post(f'/api/v1/dashboard/problem-statements/{ps_draft.id}/interest/', **auth_header(self.token_a))
        assert r_draft.status_code == status.HTTP_400_BAD_REQUEST

        # Req 16: Closed PS rejects interest
        ps_closed = self._create_ps(ps_status=ProblemStatement.Status.CLOSED)
        r_closed = self.client.post(f'/api/v1/dashboard/problem-statements/{ps_closed.id}/interest/', **auth_header(self.token_a))
        assert r_closed.status_code == status.HTTP_400_BAD_REQUEST

        # Req 17: Archived PS rejects interest
        ps_archived = self._create_ps(ps_status=ProblemStatement.Status.ARCHIVED)
        r_archived = self.client.post(f'/api/v1/dashboard/problem-statements/{ps_archived.id}/interest/', **auth_header(self.token_a))
        assert r_archived.status_code == status.HTTP_400_BAD_REQUEST

        # Req 18: Removed PS rejects interest
        ps_removed = self._create_ps(ps_status=ProblemStatement.Status.REMOVED)
        r_removed = self.client.post(f'/api/v1/dashboard/problem-statements/{ps_removed.id}/interest/', **auth_header(self.token_a))
        assert r_removed.status_code == status.HTTP_400_BAD_REQUEST

        # Req 19: Expired deadline rejects interest
        past_dl = timezone.now() - timedelta(hours=2)
        ps_expired = self._create_ps(ps_status=ProblemStatement.Status.PUBLISHED, deadline=past_dl)
        r_expired = self.client.post(f'/api/v1/dashboard/problem-statements/{ps_expired.id}/interest/', **auth_header(self.token_a))
        assert r_expired.status_code == status.HTTP_400_BAD_REQUEST

        # Req 20: Future deadline accepts interest
        future_dl = timezone.now() + timedelta(days=5)
        ps_future = self._create_ps(ps_status=ProblemStatement.Status.PUBLISHED, deadline=future_dl)
        r_future = self.client.post(f'/api/v1/dashboard/problem-statements/{ps_future.id}/interest/', **auth_header(self.token_a))
        assert r_future.status_code == status.HTTP_200_OK

    # ─────────────────────────────────────────────────────────────
    # 4. DUPLICATE & REACTIVATION TESTS (Req 21 - 23)
    # ─────────────────────────────────────────────────────────────

    def test_req_21_to_23_duplicate_and_reactivation(self):
        """Req 21-23: Duplicate returns 409; withdrawn interest reactivates in same row."""
        ps = self._create_ps(ps_status=ProblemStatement.Status.PUBLISHED)

        # Create interest
        r1 = self.client.post(f'/api/v1/dashboard/problem-statements/{ps.id}/interest/', **auth_header(self.token_a))
        assert r1.status_code == status.HTTP_200_OK

        initial_interest = ProblemStatementInterest.objects.get(problem_statement=ps, user=self.user_a)
        initial_id = initial_interest.id

        # Req 21: Duplicate active interest returns 409 Conflict
        r2 = self.client.post(f'/api/v1/dashboard/problem-statements/{ps.id}/interest/', **auth_header(self.token_a))
        assert r2.status_code == status.HTTP_409_CONFLICT
        assert ProblemStatementInterest.objects.filter(problem_statement=ps, user=self.user_a).count() == 1

        # Withdraw interest
        rw = self.client.delete(f'/api/v1/dashboard/problem-statements/{ps.id}/interest/', **auth_header(self.token_a))
        assert rw.status_code == status.HTTP_200_OK

        withdrawn_interest = ProblemStatementInterest.objects.get(problem_statement=ps, user=self.user_a)
        assert withdrawn_interest.status == ProblemStatementInterest.Status.WITHDRAWN

        # Req 22 & 23: Reactivate withdrawn interest, reusing the exact same DB row
        r_reactivate = self.client.post(
            f'/api/v1/dashboard/problem-statements/{ps.id}/interest/',
            data={"note": "Reactivating!"},
            format='json',
            **auth_header(self.token_a)
        )
        assert r_reactivate.status_code == status.HTTP_200_OK

        reactivated_interest = ProblemStatementInterest.objects.get(problem_statement=ps, user=self.user_a)
        assert reactivated_interest.status == ProblemStatementInterest.Status.INTERESTED
        assert reactivated_interest.id == initial_id  # Req 23: Same row reused
        assert ProblemStatementInterest.objects.filter(problem_statement=ps, user=self.user_a).count() == 1

    # ─────────────────────────────────────────────────────────────
    # 5. SECURITY & OWNERSHIP TESTS (Req 24 - 26)
    # ─────────────────────────────────────────────────────────────

    def test_req_24_to_26_security_and_impersonation(self):
        """Req 24-26: User isolation (Learner A cannot edit/withdraw Learner B's interest); JWT identity wins."""
        ps = self._create_ps(ps_status=ProblemStatement.Status.PUBLISHED)

        # Learner B creates interest
        r_b = self.client.post(
            f'/api/v1/dashboard/problem-statements/{ps.id}/interest/',
            data={"note": "Learner B original note"},
            format='json',
            **auth_header(self.token_b)
        )
        assert r_b.status_code == status.HTTP_200_OK

        interest_b = ProblemStatementInterest.objects.get(problem_statement=ps, user=self.user_b)

        # Req 24: Learner A cannot PATCH Learner B's interest
        r_patch = self.client.patch(
            f'/api/v1/dashboard/problem-statements/{ps.id}/interest/',
            data={"note": "Learner A tampering attempt"},
            format='json',
            **auth_header(self.token_a)
        )
        assert r_patch.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN)
        interest_b.refresh_from_db()
        assert interest_b.note == "Learner B original note"  # Unchanged

        # Req 25: Learner A cannot DELETE Learner B's interest
        r_del = self.client.delete(f'/api/v1/dashboard/problem-statements/{ps.id}/interest/', **auth_header(self.token_a))
        assert r_del.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN)
        interest_b.refresh_from_db()
        assert interest_b.status == ProblemStatementInterest.Status.INTERESTED  # Still interested

        # Req 26: Request-body user_id cannot impersonate another learner (rejected by serializer/validation)
        r_impersonate = self.client.post(
            f'/api/v1/dashboard/problem-statements/{ps.id}/interest/',
            data={"user_id": self.user_b_id, "note": "Impersonation attempt"},
            format='json',
            **auth_header(self.token_a)
        )
        assert r_impersonate.status_code == status.HTTP_400_BAD_REQUEST
        interest_b.refresh_from_db()
        assert interest_b.user_id == self.user_b_id  # Learner B's identity is safe


    # ─────────────────────────────────────────────────────────────
    # 6. EDIT INTEREST TESTS (Req 27 - 29)
    # ─────────────────────────────────────────────────────────────

    def test_req_27_to_29_edit_interest_and_validation(self):
        """Req 27-29: Learner can PATCH own active interest; invalid link rejected; protected fields locked."""
        ps = self._create_ps(ps_status=ProblemStatement.Status.PUBLISHED)

        # Create interest
        self.client.post(
            f'/api/v1/dashboard/problem-statements/{ps.id}/interest/',
            data={"note": "Initial note", "work_link": "https://github.com/initial/repo"},
            format='json',
            **auth_header(self.token_a)
        )

        # Req 27: Learner can edit their own interest
        r_edit = self.client.patch(
            f'/api/v1/dashboard/problem-statements/{ps.id}/interest/',
            data={"note": "Updated note", "work_link": "https://github.com/updated/repo"},
            format='json',
            **auth_header(self.token_a)
        )
        assert r_edit.status_code == status.HTTP_200_OK

        interest = ProblemStatementInterest.objects.get(problem_statement=ps, user=self.user_a)
        assert interest.note == "Updated note"
        assert interest.work_link == "https://github.com/updated/repo"

        # Req 28: Invalid work_link is rejected
        r_invalid_link = self.client.patch(
            f'/api/v1/dashboard/problem-statements/{ps.id}/interest/',
            data={"work_link": "invalid-url-without-scheme"},
            format='json',
            **auth_header(self.token_a)
        )
        assert r_invalid_link.status_code == status.HTTP_400_BAD_REQUEST

        # Req 29: Protected/unsupported fields cannot modify ownership or problem statement association
        r_protected = self.client.patch(
            f'/api/v1/dashboard/problem-statements/{ps.id}/interest/',
            data={"user_id": self.user_b_id, "problem_statement": "fake-ps-id"},
            format='json',
            **auth_header(self.token_a)
        )
        assert r_protected.status_code in (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST)
        interest.refresh_from_db()
        assert interest.user_id == self.user_a_id  # Ownership protected
        assert interest.problem_statement_id == ps.id  # PS association protected


    # ─────────────────────────────────────────────────────────────
    # 7. WITHDRAW TESTS (Req 30 - 33)
    # ─────────────────────────────────────────────────────────────

    def test_req_30_to_33_withdraw_interest_and_counter(self):
        """Req 30-33: Active interest transitions to WITHDRAWN; row soft-preserved; counter decremented safely."""
        ps = self._create_ps(ps_status=ProblemStatement.Status.PUBLISHED)

        # Create interest
        self.client.post(f'/api/v1/dashboard/problem-statements/{ps.id}/interest/', **auth_header(self.token_a))
        ps.refresh_from_db()
        assert ps.interest_count == 1

        interest = ProblemStatementInterest.objects.get(problem_statement=ps, user=self.user_a)
        interest_id = interest.id

        # Req 30: DELETE transitions INTERESTED -> WITHDRAWN
        r_del = self.client.delete(f'/api/v1/dashboard/problem-statements/{ps.id}/interest/', **auth_header(self.token_a))
        assert r_del.status_code == status.HTTP_200_OK

        # Req 31: Row is NOT physically deleted
        re_queried = ProblemStatementInterest.objects.filter(id=interest_id).first()
        assert re_queried is not None
        assert re_queried.status == ProblemStatementInterest.Status.WITHDRAWN

        # Req 32: interest_count decrements correctly
        ps.refresh_from_db()
        assert ps.interest_count == 0

        # Req 33: Repeated withdraw returns 404 and counter remains 0 (cannot become negative)
        r_del_again = self.client.delete(f'/api/v1/dashboard/problem-statements/{ps.id}/interest/', **auth_header(self.token_a))
        assert r_del_again.status_code == status.HTTP_404_NOT_FOUND

        ps.refresh_from_db()
        assert ps.interest_count >= 0

    # ─────────────────────────────────────────────────────────────
    # 8. MY INTERESTS TESTS (Req 34 - 36)
    # ─────────────────────────────────────────────────────────────

    def test_req_34_to_36_my_interests_feed(self):
        """Req 34-36: Learner A sees only Learner A's active interests; Learner B's are excluded; pagination valid."""
        ps1 = self._create_ps(title="PS 1", ps_status=ProblemStatement.Status.PUBLISHED)
        ps2 = self._create_ps(title="PS 2", ps_status=ProblemStatement.Status.PUBLISHED)

        # Learner A registers for PS1
        self.client.post(f'/api/v1/dashboard/problem-statements/{ps1.id}/interest/', **auth_header(self.token_a))
        # Learner B registers for PS2
        self.client.post(f'/api/v1/dashboard/problem-statements/{ps2.id}/interest/', **auth_header(self.token_b))

        # Req 34 & 35: GET /my-interests/ as Learner A returns PS1 and excludes PS2
        resp_a = self.client.get('/api/v1/dashboard/problem-statements/my-interests/', **auth_header(self.token_a))
        assert resp_a.status_code == status.HTTP_200_OK

        # Req 36: Standard pagination structure
        res_json = resp_a.json()
        assert 'response' in res_json
        data_a = res_json['response']['data']
        pagination = res_json['response']['pagination']

        ps_ids_a = [item['id'] for item in data_a]
        assert ps1.id in ps_ids_a  # Req 34: Learner A sees own interest
        assert ps2.id not in ps_ids_a  # Req 35: Learner A cannot see Learner B's interest
        assert 'count' in pagination or 'total' in pagination or 'page' in pagination

    # ─────────────────────────────────────────────────────────────
    # 9 & 10. COUNTER MATH & MULTI-LEARNER LIFECYCLE (Req 37 - 40)
    # ─────────────────────────────────────────────────────────────

    def test_req_37_to_40_counter_multi_learner_lifecycle(self):
        """Req 37-40: Sequential create/withdraw/reactivate sequence across multiple learners maintains exact counter."""
        ps = self._create_ps(ps_status=ProblemStatement.Status.PUBLISHED)
        assert ps.interest_count == 0

        # Req 37: Learner A creates interest -> counter = 1
        self.client.post(f'/api/v1/dashboard/problem-statements/{ps.id}/interest/', **auth_header(self.token_a))
        ps.refresh_from_db()
        assert ps.interest_count == 1

        # Req 40: Learner B creates interest -> counter = 2
        self.client.post(f'/api/v1/dashboard/problem-statements/{ps.id}/interest/', **auth_header(self.token_b))
        ps.refresh_from_db()
        assert ps.interest_count == 2

        # Req 38 & 40: Learner A withdraws interest -> counter = 1
        self.client.delete(f'/api/v1/dashboard/problem-statements/{ps.id}/interest/', **auth_header(self.token_a))
        ps.refresh_from_db()
        assert ps.interest_count == 1

        # Req 39 & 40: Learner A reactivates interest -> counter = 2
        self.client.post(f'/api/v1/dashboard/problem-statements/{ps.id}/interest/', **auth_header(self.token_a))
        ps.refresh_from_db()
        assert ps.interest_count == 2

    # ─────────────────────────────────────────────────────────────
    # GREPTILE REGRESSION TESTS
    # ─────────────────────────────────────────────────────────────

    def test_p1_3_interest_status_cannot_be_patched_directly(self):
        """P1-3: Client cannot bypass withdrawal logic by sending status='withdrawn' in PATCH."""
        ps = self._create_ps(ps_status=ProblemStatement.Status.PUBLISHED)
        self.client.post(f'/api/v1/dashboard/problem-statements/{ps.id}/interest/', **auth_header(self.token_a))
        ps.refresh_from_db()
        assert ps.interest_count == 1

        # Attempt to PATCH status directly
        r_patch = self.client.patch(
            f'/api/v1/dashboard/problem-statements/{ps.id}/interest/',
            data={"status": "withdrawn", "note": "New note"},
            format='json',
            **auth_header(self.token_a)
        )
        assert r_patch.status_code == status.HTTP_200_OK

        interest = ProblemStatementInterest.objects.get(problem_statement=ps, user=self.user_a)
        assert interest.status == ProblemStatementInterest.Status.INTERESTED  # Status unmutated
        ps.refresh_from_db()
        assert ps.interest_count == 1  # Counter preserved

    def test_p1_6_interest_eligibility_deadline_check(self):
        """P1-6: Learner interest submission after deadline is rejected with HTTP 400."""
        past_deadline = timezone.now() - timedelta(hours=1)
        ps = self._create_ps(ps_status=ProblemStatement.Status.PUBLISHED, deadline=past_deadline)

        r_post = self.client.post(f'/api/v1/dashboard/problem-statements/{ps.id}/interest/', **auth_header(self.token_a))
        assert r_post.status_code == status.HTTP_400_BAD_REQUEST

    def test_p1_9_company_user_cannot_register_interest(self):
        """P1-9: Company role attempting to express interest is rejected with HTTP 403."""
        ps = self._create_ps(ps_status=ProblemStatement.Status.PUBLISHED)
        company_token = make_jwt_token(self.user_a_id, roles=["Company"])

        r_post = self.client.post(f'/api/v1/dashboard/problem-statements/{ps.id}/interest/', **auth_header(company_token))
        assert r_post.status_code == status.HTTP_403_FORBIDDEN

    def test_p2_13_integer_category_and_skill_filters(self):
        """P2-13 / Finding 1: Categories and skills stored as integer/string IDs are filtered safely without ValueError on ²."""
        ps = self._create_ps(
            ps_status=ProblemStatement.Status.PUBLISHED,
            categories=[123, "abc", "²"],
            skills=[123, "python", "²"]
        )

        # Filter by integer string '123'
        r_cat_123 = self.client.get('/api/v1/dashboard/problem-statements/?category=123')
        assert r_cat_123.status_code == status.HTTP_200_OK
        ids_cat_123 = [item['id'] for item in r_cat_123.json().get('response', {}).get('data', [])]
        assert ps.id in ids_cat_123

        # Filter by string 'abc'
        r_cat_abc = self.client.get('/api/v1/dashboard/problem-statements/?category=abc')
        assert r_cat_abc.status_code == status.HTTP_200_OK
        ids_cat_abc = [item['id'] for item in r_cat_abc.json().get('response', {}).get('data', [])]
        assert ps.id in ids_cat_abc

        # Filter by unicode digit '²' (must NOT raise ValueError or cause 500)
        r_cat_unicode = self.client.get('/api/v1/dashboard/problem-statements/?category=²')
        assert r_cat_unicode.status_code == status.HTTP_200_OK
        ids_cat_unicode = [item['id'] for item in r_cat_unicode.json().get('response', {}).get('data', [])]
        assert ps.id in ids_cat_unicode

        # Filter by skill integer '123'
        r_skill_123 = self.client.get('/api/v1/dashboard/problem-statements/?skill=123')
        assert r_skill_123.status_code == status.HTTP_200_OK
        ids_skill_123 = [item['id'] for item in r_skill_123.json().get('response', {}).get('data', [])]
        assert ps.id in ids_skill_123

        # Filter by skill unicode digit '²'
        r_skill_unicode = self.client.get('/api/v1/dashboard/problem-statements/?skill=²')
        assert r_skill_unicode.status_code == status.HTTP_200_OK
        ids_skill_unicode = [item['id'] for item in r_skill_unicode.json().get('response', {}).get('data', [])]
        assert ps.id in ids_skill_unicode

    def test_p2_14_invalid_resource_link_types(self):
        """P2-14: Non-string resource links (e.g. integer) fail validation cleanly with HTTP 400."""
        from api.dashboard.problem_statement.serializers import ProblemStatementWriteSerializer
        ser = ProblemStatementWriteSerializer(data={"resources": [{"link": 123}]})
        assert not ser.is_valid()
        assert 'resources' in ser.errors
