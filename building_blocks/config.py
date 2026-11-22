"""Typed, declared configuration (ADR-048).

Every setting is declared once with its type, default, the environments that require it and
whether it's secret (mulearnbackend/config_settings.py). Values come from the environment, then
.env, as before (python-decouple). At startup every problem is reported in one error, and
`manage.py config_check --env-file <path>` reports them for an env file before a deploy.
Problem messages never contain a secret's value.

MULEARN_ENV names the environment: local (the default), dev, staging or production.
"""

from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

ENVIRONMENTS = ("local", "dev", "staging", "production")
ALL_ENVIRONMENTS = frozenset(ENVIRONMENTS)
ENV_VAR = "MULEARN_ENV"

# The values python-decouple's cast=bool accepted, so existing environments keep working.
_TRUE = frozenset({"1", "yes", "true", "on", "y", "t"})
_FALSE = frozenset({"0", "no", "false", "off", "n", "f", ""})

Source = Callable[[str], "str | None"]


class URL:
    """Setting type: an http or https URL with a host. An empty value means not configured."""


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Setting:
    name: str
    type: object = str
    default: object = None
    required_in: frozenset = frozenset()
    secret: bool = False


_declared: dict[str, Setting] = {}


def declare(*settings: Setting) -> None:
    for setting in settings:
        existing = _declared.get(setting.name)
        if existing is not None and existing != setting:
            raise ValueError(f"{setting.name} is already declared differently: {existing!r}.")
        _declared[setting.name] = setting


def declared() -> dict[str, Setting]:
    return dict(_declared)


def _shown(setting: Setting, raw: str) -> str:
    return " (the value is secret, so it isn't shown)." if setting.secret else f", not {raw!r}."


def parse(setting: Setting, raw: str):
    """Convert a raw string to the setting's type, or raise ConfigError."""
    kind = setting.type
    if kind is str:
        return raw
    if kind is bool:
        word = raw.strip().lower()
        if word in _TRUE:
            return True
        if word in _FALSE:
            return False
        raise ConfigError(f"{setting.name} must be true or false (also yes/no, on/off or 1/0){_shown(setting, raw)}")
    if kind is int:
        try:
            return int(raw.strip())
        except ValueError:
            raise ConfigError(f"{setting.name} must be a whole number{_shown(setting, raw)}") from None
    if kind == list[str]:
        return [item.strip() for item in raw.split(",")]
    if kind is URL:
        if raw == "":
            return raw
        parts = urlsplit(raw.strip())
        if parts.scheme in ("http", "https") and parts.netloc:
            return raw
        raise ConfigError(f"{setting.name} must be an http or https URL with a host{_shown(setting, raw)}")
    raise TypeError(f"{setting.name} has an unsupported type {kind!r}.")


def _environment_source(name: str) -> "str | None":
    """The environment, then .env, as decouple reads them."""
    from decouple import config as decouple_config

    return decouple_config(name, default=None)


def environment(source: Source | None = None) -> str:
    raw = (source or _environment_source)(ENV_VAR)
    if not raw:
        return "local"
    name = raw.strip().lower()
    if name not in ENVIRONMENTS:
        raise ConfigError(f"{ENV_VAR} must be one of {', '.join(ENVIRONMENTS)}, not {raw!r}.")
    return name


def value(name: str, source: Source | None = None):
    """A setting's value: parsed from the source, or its default when unset."""
    setting = _declared[name]
    raw = (source or _environment_source)(name)
    if raw is None:
        return setting.default
    return parse(setting, raw)


def get(name: str):
    """A declared setting's value, from the environment and .env."""
    return value(name)


def problems(source: Source | None = None, env: str | None = None) -> list[str]:
    """Every problem with the declared settings for ``env`` (by default the source's MULEARN_ENV)."""
    source = source or _environment_source
    found = []
    if env is None:
        try:
            env = environment(source)
        except ConfigError as error:
            found.append(str(error))
            env = "local"
    for name in sorted(_declared):
        setting = _declared[name]
        raw = source(name)
        if raw is None:
            if env in setting.required_in:
                found.append(f"{name} is required in {env} but isn't set.")
            continue
        try:
            parse(setting, raw)
        except ConfigError as error:
            found.append(str(error))
    return found


def raise_if_invalid(source: Source | None = None) -> None:
    """Stop startup with one error that lists every configuration problem."""
    found = problems(source)
    if found:
        raise ImproperlyConfigured(
            "Configuration problems:\n  - "
            + "\n  - ".join(found)
            + "\nSet them in the environment or in .env (see .env.sample), then restart."
        )
