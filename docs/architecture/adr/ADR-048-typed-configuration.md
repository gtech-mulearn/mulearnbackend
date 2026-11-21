# ADR-048: Typed, fail-fast configuration and secrets

Status: Accepted (new on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-21)
Implementation status at dev 7fd66060: not started. `mulearnbackend/settings.py` reads its settings with `decouple_config` at import time, some with no default.

## Context

Environment variables are read ad hoc across many files. Some are parsed with the wrong type, and
some are required only at import time, so a missing value crash-loops a container. Settings and
`AppConfig.ready()` also perform I/O at import.

## Options considered

- **django-environ or pydantic-settings:** a new dependency.
- **Extend `building_blocks/config`.**
- **Keep ad-hoc reads.**

## Decision

- **Every environment variable is declared once,** with its type, default, `required_in` and a
  secret marker. All reads go through the declaration, migrated by codemod.
- **`manage.py config_check --env-file <f>`** runs in CI and at deploy pre-flight against each
  environment's key list. It checks names only, never values.
- **No I/O at import:** no DNS lookups in settings, and no queries in `ready()`.
- **Production refuses to boot** with `DEBUG`, a wildcard `ALLOWED_HOSTS` or wildcard CORS.
- **Secrets** live in AWS SSM Parameter Store (SecureString) and are rendered into the container
  environment at deploy time. None are baked into images.

## Consequences

- A missing or malformed value fails the deploy pre-flight, not production.

## Revisit when

- The number of environments or services makes a dedicated secrets manager worthwhile.

## Related ADRs

[ADR-049](ADR-049-deployment-platform-and-dr.md), [ADR-051](ADR-051-toolchain.md)
