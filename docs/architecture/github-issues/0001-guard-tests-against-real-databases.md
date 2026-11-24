# Guard the test suite against real databases

| | |
|---|---|
| ID | 0001 |
| Phase / milestone | Phase 0: Stabilise and secure |
| Module | platform |
| Size | S |
| Labels | arch, phase:0, module:platform, type:chore, size:S, good first issue |
| Depends on | none |
| Blocks | 0002 |
| Repos | mulearnbackend |

## Why

The root `conftest.py` calls `django.setup()` with the project settings, so `pytest` runs against whatever database `.env` points at. Some legacy tests flush **every table** of the database they run against. A contributor who runs `pytest` with a normal `.env`, which often points at a shared development database, can wipe it.

This issue makes the test suite refuse to run against anything except SQLite or a local database whose name starts with `test_`. Every other architecture issue depends on running tests safely ([12-testing-and-quality-gates.md](../12-testing-and-quality-gates.md#running-tests-safely)).

## Before you start

- Read [Running tests safely](../12-testing-and-quality-gates.md#running-tests-safely).
- Read the root `conftest.py` and the `DATABASES` block in `mulearnbackend/settings.py` (it reads `DATABASE_ENGINE`, `DATABASE_NAME`, `DATABASE_HOST` and the rest from the environment).
- Until this issue lands, run tests only with the in-memory SQLite override shown below.
- Set up your clone as [Setting up a fresh clone](README.md#setting-up-a-fresh-clone) describes.

## What to do

1. Create `tests/db_guard.py` with one function, `assert_safe_test_database(db: dict) -> None`. It takes a Django `DATABASES["default"]` dict.
   - It returns if `db["ENGINE"]` ends with `sqlite3`.
   - It returns if `db["HOST"]` is one of `""`, `"localhost"`, `"127.0.0.1"`, `"mysql"` or `"db"` **and** `db["NAME"]` starts with `test_`.
   - Otherwise it calls `pytest.exit(message, returncode=2)`. The message names the database and host, and points to `docs/architecture/12-testing-and-quality-gates.md`.
2. In the root `conftest.py`, add a `pytest_configure(config)` hook that calls `assert_safe_test_database(settings.DATABASES["default"])`. It runs after `django.setup()` and before any test module is collected. Call it from the hook, not at import time: `pytest.exit` raised while a conftest is being imported ends with exit code 4 and a traceback instead of code 2.
3. Add `tests/test_db_guard.py` with these cases:
   - SQLite is allowed;
   - `localhost` + `test_mulearn` is allowed;
   - `localhost` + `mulearn` is refused;
   - `dev.example.com` + `test_mulearn` is refused;
   - an empty host + `mulearn` is refused.
   Assert on `pytest.exit` by catching `_pytest.outcomes.Exit`.

## Acceptance criteria

- [ ] With the SQLite override, `pytest tests/test_db_guard.py` passes.
- [ ] With `DATABASE_HOST=example.invalid` and `DATABASE_NAME=shared`, pytest stops before collecting any test and prints the refusal message. Use an unreachable host, so nothing is touched even if the guard were wrong.
- [ ] A safe-recipe run of the existing suite collects and passes the same tests as before this change.
- [ ] The message tells the reader how to run tests safely.

## How to test

```sh
DATABASE_ENGINE=django.db.backends.sqlite3 DATABASE_NAME=":memory:" DATABASE_USER= DATABASE_PASSWORD= DATABASE_HOST= DATABASE_PORT= python -m pytest tests/test_db_guard.py --import-mode=importlib
```

To check the refusal, run the same command with `DATABASE_ENGINE=django.db.backends.mysql DATABASE_HOST=example.invalid DATABASE_NAME=shared` in place of the SQLite values. Expect exit code 2 and the refusal message, with no tests collected.

## Out of scope

- Fixing the legacy tests that flush tables.
- Creating test databases or CI changes (issues 0011 and 0012).

## Notes for reviewers

This guard protects every contributor's database, so check that it runs before any test module imports models, and that it can't be bypassed by a pytest flag.
