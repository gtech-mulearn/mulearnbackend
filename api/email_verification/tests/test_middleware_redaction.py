"""Spec A §3.8: request bodies reach error.log; secrets must not."""
import json
from types import SimpleNamespace
from unittest import mock

from mulearnbackend.middlewares import UniversalErrorHandlerMiddleware, redact_body


def test_redacts_secrets_at_any_depth_and_keeps_the_rest():
    raw = json.dumps({"user": {"email": "asha@example.com", "password": "hunter22"},
                      "code": "123456", "email_verification_token": "tok",
                      "items": [{"otp": "999999"}]})
    body = json.loads(redact_body(raw))
    assert body["user"] == {"email": "asha@example.com", "password": "[REDACTED]"}
    assert body["code"] == body["email_verification_token"] == "[REDACTED]"
    assert body["items"] == [{"otp": "[REDACTED]"}]


def test_non_json_bodies_with_secrets_are_withheld():
    assert redact_body("emailOrMuid=asha&password=hunter22").startswith("[REDACTED")
    assert redact_body("plain text") == "plain text"


def test_log_exception_never_writes_a_password():
    request = SimpleNamespace(
        _body=json.dumps({"password": "hunter22", "email": "asha@example.com"}).encode(),
        method="POST", path="/api/v1/register/", auth=None,
    )
    middleware = UniversalErrorHandlerMiddleware(lambda r: None)
    with mock.patch("mulearnbackend.middlewares.logger") as logger, mock.patch("builtins.print"):
        middleware.log_exception(request, ValueError("boom"))
    logged = logger.error.call_args.args[0]
    assert "hunter22" not in logged
    assert "asha@example.com" in logged
