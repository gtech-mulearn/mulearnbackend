"""Spec B §3.7: one shared budget per minute, a per-person limit, one sign-in per subject at a time."""
from unittest import mock

import pytest

from api.integrations.partner_sso import ratelimit
from api.integrations.partner_sso.errors import PartnerError

T0 = 1_800_000_000  # a minute boundary


@pytest.fixture
def clock():
    current = {"now": T0}
    with mock.patch.object(ratelimit, "_now", lambda: current["now"]):
        yield current


def test_the_shared_budget_allows_the_limit_then_says_how_long_to_wait(clock):
    for _ in range(3):
        assert ratelimit.take_partner_call("p", 3) is None
    clock["now"] += 20
    assert ratelimit.take_partner_call("p", 3) == 40


def test_the_budget_resets_every_minute(clock):
    for _ in range(3):
        ratelimit.take_partner_call("p", 3)
    clock["now"] += 60
    assert ratelimit.take_partner_call("p", 3) is None


def test_each_person_gets_ten_attempts_per_ten_minutes(clock):
    for _ in range(10):
        assert ratelimit.take_actor_attempt("p", "u-1") is None
    assert ratelimit.take_actor_attempt("p", "u-1") == 600
    assert ratelimit.take_actor_attempt("p", "u-2") is None


def test_one_sign_in_per_subject_at_a_time():
    with ratelimit.link_lock("p", "user:u-1"):
        with pytest.raises(PartnerError) as error:
            with ratelimit.link_lock("p", "user:u-1"):
                pass
        assert error.value.code == "in_progress"
    with ratelimit.link_lock("p", "user:u-1"):
        pass  # released after the first block
