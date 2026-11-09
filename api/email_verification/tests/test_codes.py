"""Spec A §3.2: the code primitive and every limit it enforces."""
from unittest import mock

import pytest
from django.core.cache import cache
from django.test import override_settings

from api.email_verification import codes
from api.email_verification.errors import VerificationError

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "email-codes"}}
EMAIL = "asha@example.com"
T0 = 1_800_000_000  # on an hour boundary


@pytest.fixture(autouse=True)
def isolated_cache():
    with override_settings(CACHES=LOCMEM):
        cache.clear()
        yield
        cache.clear()


@pytest.fixture
def clock():
    current = {"now": T0}
    with mock.patch.object(codes, "_now", lambda: current["now"]):
        yield current


def send(purpose="signup", subject=EMAIL, email=EMAIL):
    delivered = []
    sent = codes.send_code(purpose, subject, email, delivered.append)
    return sent, delivered[0]


def wrong(code):
    return "000000" if code != "000000" else "111111"


def test_code_is_six_digits_and_only_its_hmac_is_stored(clock):
    sent, code = send()
    assert sent == codes.SentCode(expires_in=600, resend_after=60)
    assert len(code) == 6 and code.isdigit()
    stored = cache.get(codes._code_key("signup", EMAIL))
    assert code not in str(stored)
    assert stored["email"] == EMAIL


def test_correct_code_returns_the_email_exactly_once(clock):
    _, code = send()
    assert codes.verify_code("signup", EMAIL, code) == EMAIL
    with pytest.raises(VerificationError) as error:
        codes.verify_code("signup", EMAIL, code)
    assert error.value.code == "code_expired"


def test_a_code_pasted_with_spaces_or_dashes_is_accepted(clock):
    _, code = send()
    assert codes.verify_code("signup", EMAIL, f"{code[:3]} - {code[3:]}") == EMAIL


def test_wrong_codes_count_down_then_kill_the_code(clock):
    _, code = send()
    for expected_left in (4, 3, 2, 1, 0):
        with pytest.raises(VerificationError) as error:
            codes.verify_code("signup", EMAIL, wrong(code))
        assert error.value.code == "invalid_code"
        assert error.value.extra["attempts_left"] == expected_left
    with pytest.raises(VerificationError) as error:
        codes.verify_code("signup", EMAIL, code)
    assert error.value.code == "code_expired"


def test_codes_expire_after_ten_minutes(clock):
    _, code = send()
    clock["now"] += 601
    with pytest.raises(VerificationError) as error:
        codes.verify_code("signup", EMAIL, code)
    assert error.value.code == "code_expired"


def test_resend_waits_sixty_seconds(clock):
    send()
    with pytest.raises(VerificationError) as error:
        send()
    assert error.value.code == "code_cooldown"
    assert error.value.extra["retry_after"] == 60
    clock["now"] += 61
    send()


def test_at_most_five_codes_per_address_per_hour_across_purposes(clock):
    for _ in range(5):
        send(purpose="signup")
        clock["now"] += 61
    with pytest.raises(VerificationError) as error:
        send(purpose="account", subject="u-1")
    assert error.value.code == "code_rate_limited"
    assert 0 < error.value.extra["retry_after"] <= 3600


def test_a_new_code_replaces_the_old_one(clock):
    _, first = send()
    clock["now"] += 61
    _, second = send()
    if first != second:
        with pytest.raises(VerificationError):
            codes.verify_code("signup", EMAIL, first)
    assert codes.verify_code("signup", EMAIL, second) == EMAIL


def test_failed_delivery_clears_the_code_and_charges_nothing(clock):
    def broken(code):
        raise ConnectionError("smtp down")

    with pytest.raises(codes.MailDeliveryFailed):
        codes.send_code("signup", EMAIL, EMAIL, broken)
    assert cache.get(codes._code_key("signup", EMAIL)) is None
    send()  # no cooldown and no hourly charge were taken


def test_unknown_purpose_is_a_programming_error(clock):
    with pytest.raises(ValueError):
        codes.send_code("other", EMAIL, EMAIL, lambda code: None)


def test_racing_wrong_guesses_each_use_up_an_attempt(clock):
    # Concurrent requests all read the code before any of them writes. Serve
    # every read of the code from one snapshot to reproduce that.
    _, code = send()
    key = codes._code_key("signup", EMAIL)
    snapshot = cache.get(key)
    real_get = cache.get
    with mock.patch.object(codes.cache, "get", lambda k, *a, **kw: snapshot if k == key else real_get(k, *a, **kw)):
        for _ in range(codes.MAX_ATTEMPTS):
            with pytest.raises(VerificationError):
                codes.verify_code("signup", EMAIL, wrong(code))
        with pytest.raises(VerificationError):
            codes.verify_code("signup", EMAIL, code)  # the right code, too late


def test_a_send_racing_another_mails_no_second_code(clock):
    outcomes = []

    def deliver(code):
        # A second request arrives while the first is still mailing.
        try:
            codes.send_code("signup", EMAIL, EMAIL, lambda c: outcomes.append("second code mailed"))
        except VerificationError as error:
            outcomes.append(error.code)

    codes.send_code("signup", EMAIL, EMAIL, deliver)
    assert outcomes == ["code_cooldown"]


def test_racing_sends_cannot_pass_the_hourly_cap(clock):
    for _ in range(codes.MAX_SENDS_PER_HOUR - 1):
        send(purpose="signup")
        clock["now"] += 61
    outcomes = []

    def deliver(code):
        # Another purpose for the same inbox, while the fifth code is mailing.
        try:
            codes.send_code("account", "u-1", EMAIL, lambda c: outcomes.append("sixth code mailed"))
        except VerificationError as error:
            outcomes.append(error.code)

    codes.send_code("signup", EMAIL, EMAIL, deliver)
    assert outcomes == ["code_rate_limited"]
