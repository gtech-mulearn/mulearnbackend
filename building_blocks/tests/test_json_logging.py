import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings

from building_blocks.observability import context
from building_blocks.observability.logging import REDACTED, JsonFormatter

ROOT = Path(__file__).resolve().parents[2]
SECRETS = {
    "password": "hunter2-secret",
    "token": "tok-secret-123",
    "otp": "424242",
    "email": "person@example.com",
    "phone": "+919999999999",
    "muid": "person@mulearn",
}


def record(msg="hello %s", args=("world",), extra=None, exc_info=None):
    item = logging.LogRecord("tests.logger", logging.WARNING, __file__, 1, msg, args, exc_info)
    for key, value in (extra or {}).items():
        setattr(item, key, value)
    return item


def render(item):
    return JsonFormatter().format(item)


def test_a_line_has_the_standard_fields():
    token = context.request_id.set("req_abc12345")
    try:
        line = json.loads(render(record()))
    finally:
        context.request_id.reset(token)

    assert line["level"] == "WARNING"
    assert line["logger"] == "tests.logger"
    assert line["message"] == "hello world"
    assert line["request_id"] == "req_abc12345"
    assert line["user_id"] is None
    assert line["trace_id"] is None
    assert line["time"].endswith("Z")


def test_the_user_id_comes_from_the_context():
    token = context.user_id.set("user-1")
    try:
        assert json.loads(render(record()))["user_id"] == "user-1"
    finally:
        context.user_id.reset(token)


def test_sensitive_extra_keys_are_redacted():
    output = render(record(extra=SECRETS))
    line = json.loads(output)

    for key, secret in SECRETS.items():
        assert line[key] == REDACTED
        assert secret not in output


@pytest.mark.parametrize("key", ["accessToken", "refresh_token", "user_email", "phone_number", "new-password", "OTP"])
def test_variants_of_sensitive_keys_are_redacted(key):
    output = render(record(extra={key: "secret-value-xyz"}))

    assert json.loads(output)[key] == REDACTED
    assert "secret-value-xyz" not in output


def test_sensitive_keys_inside_nested_extra_data_are_redacted():
    extra = {"payload": {"user": {"email": "person@example.com", "name": "Person"}, "items": [{"otp": "424242"}]}}
    output = render(record(extra=extra))
    line = json.loads(output)

    assert line["payload"]["user"] == {"email": REDACTED, "name": "Person"}
    assert line["payload"]["items"] == [{"otp": REDACTED}]
    assert "person@example.com" not in output
    assert "424242" not in output


def test_a_dict_message_is_redacted():
    output = render(record(msg={"event": "login", "password": "hunter2-secret"}, args=()))

    assert json.loads(output)["message"] == {"event": "login", "password": REDACTED}
    assert "hunter2-secret" not in output


def test_other_extra_keys_are_kept():
    line = json.loads(render(record(extra={"route": "/api/v1/x", "footprint": 3, "status_code": 200})))

    assert (line["route"], line["footprint"], line["status_code"]) == ("/api/v1/x", 3, 200)


def test_an_exception_is_included():
    try:
        raise ValueError("bad input")
    except ValueError:
        line = json.loads(render(record(exc_info=sys.exc_info())))

    assert "ValueError: bad input" in line["exception"]


def test_values_that_arent_json_are_stringified():
    assert json.loads(render(record(extra={"path": Path("a/b")})))["path"] == str(Path("a/b"))


def test_log_format_defaults_to_text_so_nothing_changes():
    assert settings.LOG_FORMAT == "text"
    assert {handler["formatter"] for handler in settings.LOGGING["handlers"].values()} == {"verbose"}


def run_django(tmp_path, log_format, code):
    env = {
        **os.environ,
        "LOG_FORMAT": log_format,
        "LOGGER_DIR_PATH": str(tmp_path),
        "LOG_LEVEL": "INFO",
        "DATABASE_ENGINE": "django.db.backends.sqlite3",
        "DATABASE_NAME": ":memory:",
        "DJANGO_SETTINGS_MODULE": "mulearnbackend.settings",
    }
    script = "import django; django.setup()\n" + code
    return subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=env, capture_output=True, text=True)


def test_with_log_format_json_log_lines_are_json_with_the_request_id(tmp_path):
    result = run_django(
        tmp_path,
        "json",
        "import logging\n"
        "from building_blocks.observability import context\n"
        "context.request_id.set('req_fromsubprocess')\n"
        "logging.getLogger('tests.json').warning('signed in', extra={'email': 'person@example.com'})\n",
    )

    assert result.returncode == 0, result.stderr
    lines = [json.loads(line) for line in (tmp_path / "root.log").read_text(encoding="utf-8").splitlines()]
    ours = [line for line in lines if line["logger"] == "tests.json"]
    assert ours == [ours[0]]
    assert ours[0]["request_id"] == "req_fromsubprocess"
    assert ours[0]["email"] == REDACTED
    assert "person@example.com" not in (tmp_path / "root.log").read_text(encoding="utf-8")


def test_an_unknown_log_format_stops_startup(tmp_path):
    result = run_django(tmp_path, "yaml", "")

    assert result.returncode != 0
    assert "LOG_FORMAT" in result.stderr
