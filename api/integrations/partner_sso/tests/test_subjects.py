"""Spec B §3.1: who may act for which partner account. Query helpers are patched."""
from types import SimpleNamespace
from unittest import mock

from api.integrations.partner_sso import subjects
from api.integrations.partner_sso.subjects import SubjectKind, resolve

ASHA = SimpleNamespace(id="u-1", full_name="Asha Nair")
RAVI = SimpleNamespace(id="u-2", full_name="Ravi Menon")


def patched(**helpers):
    return mock.patch.multiple(subjects, **{name: mock.Mock(return_value=value) for name, value in helpers.items()})


class TestLearner:
    def test_a_verified_learner_manages_their_own_account(self):
        with patched(_active_user=ASHA, _has_active_role=True):
            result = resolve(SubjectKind.LEARNER, "u-1")
        assert (result.can_manage, result.subject_type, result.subject_id, result.manager) == (True, "user", "u-1", ASHA)

    def test_non_learners_never_see_the_card(self):
        with patched(_active_user=ASHA, _has_active_role=False):
            result = resolve(SubjectKind.LEARNER, "u-1")
        assert result.reason == "not_learner" and result.hidden and not result.can_manage

    def test_suspended_users_are_hidden(self):
        with patched(_active_user=None):
            assert resolve(SubjectKind.LEARNER, "u-1").reason == "suspended"


class TestCompany:
    def test_the_verified_owner_manages_it(self):
        company = SimpleNamespace(id="c-1", name="Acme Tech", status="verified")
        with patched(_owned_company=company, _active_user=ASHA):
            result = resolve(SubjectKind.COMPANY, "u-1")
        assert (result.can_manage, result.subject_type, result.subject_id, result.subject_name) == (True, "company", "c-1", "Acme Tech")

    def test_an_unverified_company_cannot_connect_yet(self):
        company = SimpleNamespace(id="c-1", name="Acme Tech", status="pending")
        with patched(_owned_company=company):
            result = resolve(SubjectKind.COMPANY, "u-1")
        assert result.reason == "company_not_verified" and not result.hidden and not result.can_manage
        assert result.message == "Available once µLearn verifies your company."

    def test_co_admins_see_it_read_only(self):
        company = SimpleNamespace(id="c-1", name="Acme Tech", company_user=RAVI)
        with patched(_owned_company=None, _delegated_company=company):
            result = resolve(SubjectKind.COMPANY, "u-1")
        assert (result.reason, result.manager, result.can_manage, result.hidden) == ("not_owner", RAVI, False, False)

    def test_everyone_else_is_hidden(self):
        with patched(_owned_company=None, _delegated_company=None):
            assert resolve(SubjectKind.COMPANY, "u-1").hidden


class TestCollege:
    link = SimpleNamespace(org=SimpleNamespace(id="o-1", title="St Xavier's College"))

    def test_the_lead_enabler_manages_it(self):
        with patched(_campus_link=self.link, _has_active_role=True, _lead_enablers=[ASHA]):
            result = resolve(SubjectKind.COLLEGE, "u-1")
        assert (result.can_manage, result.subject_type, result.subject_id, result.manager) == (True, "organization", "o-1", ASHA)

    def test_other_staff_see_it_read_only(self):
        with patched(_campus_link=self.link, _has_active_role=True, _lead_enablers=[RAVI]):
            result = resolve(SubjectKind.COLLEGE, "u-1")
        assert (result.reason, result.manager, result.can_manage) == ("not_lead_enabler", RAVI, False)

    def test_two_lead_enablers_block_everyone(self):
        with patched(_campus_link=self.link, _has_active_role=True, _lead_enablers=[ASHA, RAVI]):
            result = resolve(SubjectKind.COLLEGE, "u-1")
        assert result.reason == "multiple_lead_enablers" and not result.can_manage

    def test_a_college_without_a_lead_enabler(self):
        with patched(_campus_link=self.link, _has_active_role=True, _lead_enablers=[]):
            assert resolve(SubjectKind.COLLEGE, "u-1").reason == "no_lead_enabler"

    def test_non_staff_are_hidden(self):
        with patched(_campus_link=self.link, _has_active_role=False):
            result = resolve(SubjectKind.COLLEGE, "u-1")
        assert result.reason == "not_campus_staff" and result.hidden
