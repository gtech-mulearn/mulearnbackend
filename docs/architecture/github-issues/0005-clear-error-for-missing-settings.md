# Fail with a clear message when a required setting is missing

| | |
|---|---|
| ID | 0005 |
| Phase / milestone | Phase 0: Stabilise and secure |
| Module | platform |
| Size | S |
| Labels | arch, phase:0, module:platform, type:chore, size:S, good first issue |
| Depends on | none |
| Blocks | 0020 |
| Repos | mulearnbackend |

## Why

`mulearnbackend/settings.py` reads 28 settings with `decouple_config(...)` and no default, for example `R2_PUBLIC_BASE_URL`, `SYSTEM_ADMIN_ID` and the email settings. If one is missing, the import fails with a bare `UndefinedValueError` naming only the first missing value. Every container (web, worker, beat) then crash-loops. Collecting them and failing once, with the full list, turns a crash-loop into a clear message.

## Before you start

- Read the top of `mulearnbackend/settings.py` and every `decouple_config("...")` call without a `default=`.
- This is a stop-gap: typed configuration (issue 0020) replaces it later.

## What to do

1. In `mulearnbackend/settings.py`, add a small helper `_required(name: str) -> str` that reads the value with `decouple_config(name, default=None)` and records the name in `_MISSING` when it is absent.
2. Replace each `decouple_config("NAME")` that has no default with `_required("NAME")`. Leave calls that have a default alone.
3. After the last setting, if `_MISSING` is not empty, raise `django.core.exceptions.ImproperlyConfigured` listing every missing name, sorted, in one message.
4. Add `tests/test_settings_required.py`, which runs the helper logic as a plain function (no Django setup) and checks that two missing names are both reported.

## Acceptance criteria

- [ ] Starting with two required values unset fails once, with an `ImproperlyConfigured` message listing both names.
- [ ] Starting with all values set behaves exactly as before.
- [ ] No setting gains a default it didn't have.

## How to test

```sh
DATABASE_ENGINE=django.db.backends.sqlite3 DATABASE_NAME=":memory:" DATABASE_USER= DATABASE_PASSWORD= DATABASE_HOST= DATABASE_PORT= python -m pytest tests/test_settings_required.py --import-mode=importlib
```

## Out of scope

- Adding types or defaults to settings (issue 0020).
- Changing which settings are required.

## Notes for reviewers

Make sure behaviour with a complete environment is unchanged. Settings imports are fragile.
