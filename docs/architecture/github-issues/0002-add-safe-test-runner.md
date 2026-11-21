# Add a safe test runner script

| | |
|---|---|
| ID | 0002 |
| Phase / milestone | Phase 0: Stabilise and secure |
| Module | platform |
| Size | S |
| Labels | arch, phase:0, module:platform, type:chore, size:S |
| Depends on | 0001 |
| Blocks | 0004, 0009, 0011 |
| Repos | mulearnbackend |

## Why

Typing the SQLite override by hand is error-prone, and the MySQL tier needs its own settings. A single safe runner means every issue can say `scripts/test.sh <paths>` and nobody has to remember environment variables ([12-testing-and-quality-gates.md](../12-testing-and-quality-gates.md#running-tests-safely)).

## Before you start

- Issue 0001 (the guard) must be merged.
- `scripts/` already exists at the repository root.

## What to do

1. Create `scripts/test.sh` (bash, executable):
   - **Default (SQLite tier).** Export `DATABASE_ENGINE=django.db.backends.sqlite3`, `DATABASE_NAME=:memory:` and empty `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST` and `DATABASE_PORT`, then run `python -m pytest "$@" --import-mode=importlib -m "not mysql"`.
   - **`--mysql` as the first argument.** Export `DATABASE_ENGINE=django.db.backends.mysql`, `DATABASE_HOST=${TEST_DB_HOST:-127.0.0.1}`, `DATABASE_PORT=${TEST_DB_PORT:-3306}`, `DATABASE_NAME=${TEST_DB_NAME:-test_mulearn}`, `DATABASE_USER=${TEST_DB_USER:-root}` and `DATABASE_PASSWORD=${TEST_DB_PASSWORD:-local-only}`, then run pytest with `-m mysql`. The guard from 0001 still applies.
2. Create `scripts/test.ps1` with the same behaviour for PowerShell, using `-Mysql` as a switch.
3. Create `pytest.ini` at the repository root (there is no pytest configuration today) and register the `mysql` marker in it, so `-m mysql` doesn't warn.
4. Before running pytest, both scripts:
   - create the log directory (`LOGGER_DIR_PATH`, `./logs` in `.env.sample`) if it is missing, because the logging settings fail at startup without it;
   - stop with a one-line hint if `.env` is missing ("copy `.env.sample` to `.env`") or `pytest` isn't installed.
5. Add a short "Running tests" section to the top of `scripts/test.sh` as comments.

## Acceptance criteria

- [ ] `scripts/test.sh tests/test_db_guard.py` passes.
- [ ] `scripts/test.sh` ignores any `DATABASE_*` values in `.env` or the environment for the SQLite tier.
- [ ] `scripts/test.sh --mysql` with no local MySQL fails fast with a connection error, not a hang. With a non-`test_` name, it is refused by the guard.
- [ ] `scripts/test.ps1` behaves the same on Windows PowerShell.

## How to test

```sh
scripts/test.sh tests/test_db_guard.py
```

## Out of scope

- Starting MySQL locally (issue 0004).
- CI (issue 0011).

## Notes for reviewers

Check that the SQLite tier can never pick up a real database from `.env`. `decouple` reads environment variables before `.env`, so exported variables must win.
