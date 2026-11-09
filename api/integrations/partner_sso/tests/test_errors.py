import pytest

from api.integrations.partner_sso.errors import PartnerError, error_response


def test_default_messages_name_the_partner():
    assert PartnerError("partner_busy").text("Futuremug") == "Futuremug is busy right now. Try again in a minute."


def test_partner_supplied_text_is_used_verbatim_even_with_braces():
    assert PartnerError("partner_conflict", message="Email {in} use").text("Futuremug") == "Email {in} use"


def test_unknown_codes_are_programming_errors():
    with pytest.raises(ValueError):
        PartnerError("nope")


def test_error_response_uses_the_standard_envelope():
    response = error_response(PartnerError("rate_limited", retry_after=42), "Futuremug")
    assert response.status_code == 429
    assert response.data["statusCode"] == 429
    assert response.data["message"]["error_code"] == "rate_limited"
    assert response.data["response"] == {"retry_after": 42}


def test_http_status_can_be_overridden():
    assert error_response(PartnerError("partner_unavailable", http_status=502), "Futuremug").status_code == 502
