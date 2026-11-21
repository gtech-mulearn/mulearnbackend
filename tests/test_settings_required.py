import pytest
from django.core.exceptions import ImproperlyConfigured

from mulearnbackend.required_settings import make_required, raise_if_missing


def reader(values):
    """Mimic decouple's config(): the value if set, otherwise the default."""
    return lambda name, default=None: values.get(name, default)


def test_every_missing_setting_is_reported_once_and_sorted():
    missing = []
    required = make_required(reader({"SECRET_KEY": "x"}), missing)

    assert required("SECRET_KEY") == "x"
    assert required("REDIS_PORT") is None
    assert required("EMAIL_HOST") is None

    with pytest.raises(ImproperlyConfigured) as error:
        raise_if_missing(missing)
    message = str(error.value)
    assert "EMAIL_HOST, REDIS_PORT" in message
    assert "SECRET_KEY" not in message


def test_nothing_is_raised_when_every_setting_is_present():
    missing = []
    required = make_required(reader({"A": "1", "B": ""}), missing)

    assert required("A") == "1"
    assert required("B") == "", "an empty value is set, as before"
    raise_if_missing(missing)


def test_cast_applies_only_to_present_values():
    missing = []
    required = make_required(reader({"HOSTS": "a, b"}), missing)

    assert required("HOSTS", cast=lambda v: [s.strip() for s in v.split(",")]) == ["a", "b"]
    assert required("ABSENT", cast=int) is None
    assert missing == ["ABSENT"]
