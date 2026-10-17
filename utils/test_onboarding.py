"""
Tests for the onboarding-completeness rule.

Standalone under pytest — `utils.onboarding` has no Django imports:

    pytest utils/test_onboarding.py

This rule decides whether someone is sent into an onboarding flow. Getting it
wrong in one direction traps a finished member in a loop; in the other it lets
an unfinished one through. Both are visible to every app that signs people in,
which is why the rule is stated once rather than per client.
"""

from utils.onboarding import (
    STATE_COMPLETE,
    STATE_INCOMPLETE,
    STEP_INTERESTS,
    onboarding_status,
)


class TestIncomplete:
    def test_express_signup_has_onboarding_to_do(self):
        # Someone who signed up through a partner app: real member, real muid,
        # no interests yet. This is the case the whole feature exists for.
        result = onboarding_status(roles=["Mulearner"], domain_count=0)
        assert result["state"] == STATE_INCOMPLETE
        assert result["missing"] == [STEP_INTERESTS]
        assert result["exempt"] is False

    def test_no_roles_at_all_still_evaluates(self):
        # Defensive: a member with no role link must not crash the rule.
        assert onboarding_status(roles=[], domain_count=0)["state"] == STATE_INCOMPLETE

    def test_roles_none_is_treated_as_no_roles(self):
        assert onboarding_status(roles=None, domain_count=0)["state"] == STATE_INCOMPLETE


class TestComplete:
    def test_one_domain_is_enough(self):
        # Matches the existing browser rule exactly: length > 0, not "several".
        result = onboarding_status(roles=["Mulearner"], domain_count=1)
        assert result["state"] == STATE_COMPLETE
        assert result["missing"] == []

    def test_many_domains_is_complete(self):
        assert onboarding_status(roles=["Mulearner"], domain_count=7)["state"] == STATE_COMPLETE


class TestCompanyExemption:
    def test_a_company_with_no_domains_is_not_sent_to_onboarding(self):
        # Companies verify through their own flow. Routing them into the
        # student interest picker is what the dashboard's hardcoded exemption
        # was preventing, and it must survive being moved server-side.
        result = onboarding_status(roles=["Company"], domain_count=0)
        assert result["state"] == STATE_COMPLETE
        assert result["missing"] == []

    def test_exemption_is_reported_separately_from_completion(self):
        # A client must be able to distinguish "finished the checklist" from
        # "this checklist does not apply", rather than inferring it from an
        # empty missing list.
        company = onboarding_status(roles=["Company"], domain_count=0)
        finished = onboarding_status(roles=["Mulearner"], domain_count=2)
        assert company["exempt"] is True
        assert finished["exempt"] is False
        assert company["state"] == finished["state"] == STATE_COMPLETE

    def test_exemption_applies_alongside_other_roles(self):
        result = onboarding_status(roles=["Mulearner", "Company"], domain_count=0)
        assert result["exempt"] is True

    def test_a_similar_role_name_is_not_exempt(self):
        # Guards against a loose match: only the exact role is exempt.
        result = onboarding_status(roles=["Company Mentor"], domain_count=0)
        assert result["exempt"] is False
        assert result["state"] == STATE_INCOMPLETE


class TestShape:
    def test_missing_is_a_list_a_client_can_walk(self):
        result = onboarding_status(roles=["Mulearner"], domain_count=0)
        assert isinstance(result["missing"], list)
        assert all(isinstance(step, str) for step in result["missing"])

    def test_keys_are_stable(self):
        # Clients match on these. Adding is fine; renaming breaks them.
        assert set(onboarding_status(roles=[], domain_count=0)) == {
            "state", "missing", "exempt",
        }
