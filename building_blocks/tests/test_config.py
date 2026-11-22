import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

from building_blocks import config
from building_blocks.config import URL, ConfigError, Setting

ROOT = Path(__file__).resolve().parents[2]
SETTINGS = ROOT / "mulearnbackend" / "settings.py"


@pytest.fixture
def declared(monkeypatch):
    """An empty registry for the test; returns declare()."""
    monkeypatch.setattr(config, "_declared", {})
    return config.declare


def source(**values):
    return values.get


@pytest.mark.parametrize("raw", ["true", "True", "TRUE", "1", "yes", "Yes", "on", "y", "t"])
def test_true_values(raw):
    assert config.parse(Setting("FLAG", bool), raw) is True


@pytest.mark.parametrize("raw", ["false", "False", "FALSE", "0", "no", "No", "off", "n", "f", ""])
def test_false_values(raw):
    assert config.parse(Setting("FLAG", bool), raw) is False


def test_the_string_false_is_false():
    # The bug this fixes: EMAIL_USE_TLS was read as a string, and "False" is truthy.
    assert config.parse(Setting("EMAIL_USE_TLS", bool), "False") is False


def test_a_bool_that_isnt_one_is_refused():
    with pytest.raises(ConfigError, match="FLAG"):
        config.parse(Setting("FLAG", bool), "maybe")


def test_ints_lists_urls_and_strings_are_parsed():
    assert config.parse(Setting("PORT", int), " 587 ") == 587
    assert config.parse(Setting("HOSTS", list[str]), "a.org, b.org,c.org") == ["a.org", "b.org", "c.org"]
    assert config.parse(Setting("BASE", URL), "https://api.example.com/v1") == "https://api.example.com/v1"
    assert config.parse(Setting("NAME", str), " kept as is ") == " kept as is "


@pytest.mark.parametrize(("kind", "raw"), [(int, "five"), (URL, "api.example.com"), (URL, "ftp://example.com")])
def test_invalid_values_are_refused(kind, raw):
    with pytest.raises(ConfigError, match="VALUE"):
        config.parse(Setting("VALUE", kind), raw)


def test_an_empty_url_means_not_configured():
    assert config.parse(Setting("BASE", URL), "") == ""


def test_an_unset_setting_takes_its_default(declared):
    declared(Setting("THRESHOLD", int, default=500))

    assert config.problems(source(), "production") == []
    assert config.value("THRESHOLD", source()) == 500


def test_a_missing_required_value_is_a_problem(declared):
    declared(Setting("SECRET_KEY", str, required_in=config.ALL_ENVIRONMENTS, secret=True))

    assert config.problems(source(), "local") == ["SECRET_KEY is required in local but isn't set."]


def test_a_value_required_only_in_production(declared):
    declared(Setting("RAZORPAY_SECRET", str, required_in=frozenset({"production"}), secret=True))

    assert config.problems(source(), "local") == []
    assert config.problems(source(), "staging") == []
    assert config.problems(source(), "production") == ["RAZORPAY_SECRET is required in production but isn't set."]


def test_every_problem_is_reported_at_once(declared):
    declared(
        Setting("A", str, required_in=config.ALL_ENVIRONMENTS),
        Setting("B", str, required_in=config.ALL_ENVIRONMENTS),
        Setting("PORT", int),
    )

    assert config.problems(source(PORT="x"), "dev") == [
        "A is required in dev but isn't set.",
        "B is required in dev but isn't set.",
        "PORT must be a whole number, not 'x'.",
    ]


def test_a_secret_value_is_never_printed(declared):
    declared(Setting("API_KEY_COUNT", int, secret=True), Setting("WEBHOOK", URL, secret=True))
    problems = config.problems(source(API_KEY_COUNT="sk_live_123", WEBHOOK="sk_live_456"), "local")

    assert len(problems) == 2
    assert not any("sk_live" in problem for problem in problems)
    assert "API_KEY_COUNT must be a whole number (the value is secret, so it isn't shown)." in problems


def test_the_environment_comes_from_mulearn_env(declared):
    assert config.environment(source()) == "local"
    assert config.environment(source(MULEARN_ENV="Production")) == "production"
    assert config.problems(source(MULEARN_ENV="prod"), None) == [
        "MULEARN_ENV must be one of local, dev, staging, production, not 'prod'."
    ]


def test_raise_if_invalid_lists_every_problem(declared):
    required = config.ALL_ENVIRONMENTS
    declared(Setting("A", str, required_in=required), Setting("B", str, required_in=required))

    with pytest.raises(ImproperlyConfigured) as error:
        config.raise_if_invalid(source())

    assert "A is required" in str(error.value)
    assert "B is required" in str(error.value)


def test_a_conflicting_declaration_is_refused(declared):
    declared(Setting("A", str))

    with pytest.raises(ValueError, match="A"):
        declared(Setting("A", int))


def test_an_undeclared_setting_cant_be_read(declared):
    with pytest.raises(KeyError, match="NOPE"):
        config.value("NOPE", source())


def test_settings_reads_every_value_through_config():
    tree = ast.parse(SETTINGS.read_text(encoding="utf-8"))
    names = [
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "attr", None) == "get"
        and getattr(node.func.value, "id", None) == "config"
    ]
    source_text = SETTINGS.read_text(encoding="utf-8")

    assert "decouple_config(" not in source_text
    assert "_required(" not in source_text
    assert names
    assert set(names) <= set(config.declared())


def test_every_declared_setting_is_read_by_settings():
    import mulearnbackend.settings  # noqa: F401  declares them

    source_text = SETTINGS.read_text(encoding="utf-8")
    unread = [name for name in config.declared() if f'config.get("{name}")' not in source_text]
    assert unread == ["MULEARN_ENV"]


def boot(**env):
    script = "import django; django.setup(); from django.conf import settings; print(repr(settings.EMAIL_USE_TLS))"
    environment = {**os.environ, "DATABASE_ENGINE": "django.db.backends.sqlite3", "DATABASE_NAME": ":memory:", **env}
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip().splitlines()[-1]


def test_email_use_tls_false_now_turns_tls_off():
    assert boot(EMAIL_USE_TLS="False") == "False"
    assert boot(EMAIL_USE_TLS="True") == "True"
