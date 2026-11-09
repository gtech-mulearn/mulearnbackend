from django.core import signing

from api.email_verification import tokens


def test_token_round_trips_the_normalised_email():
    token = tokens.make_signup_token("  Asha@Example.COM ")
    assert tokens.read_signup_token(token) == "asha@example.com"


def test_token_matches_regardless_of_case():
    token = tokens.make_signup_token("asha@example.com")
    assert tokens.signup_token_matches(token, "Asha@Example.com")
    assert not tokens.signup_token_matches(token, "other@example.com")


def test_tampered_foreign_and_missing_tokens_never_match():
    token = tokens.make_signup_token("asha@example.com")
    assert not tokens.signup_token_matches(token[:-2] + "xx", "asha@example.com")
    foreign = signing.dumps({"email": "asha@example.com"}, salt="something-else")
    assert not tokens.signup_token_matches(foreign, "asha@example.com")
    assert not tokens.signup_token_matches(None, "asha@example.com")
    assert not tokens.signup_token_matches("", "asha@example.com")


def test_expired_token_is_rejected():
    token = tokens.make_signup_token("asha@example.com")
    assert tokens.read_signup_token(token, max_age=-1) is None


def test_a_token_that_is_not_a_string_is_just_invalid():
    # JSON bodies can carry any type; a public endpoint must not crash on one.
    for junk in (5, ["token"], {"email": "asha@example.com"}):
        assert tokens.read_signup_token(junk) is None
        assert tokens.signup_token_matches(junk, "asha@example.com") is False
