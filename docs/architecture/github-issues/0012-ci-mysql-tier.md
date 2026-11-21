# Add a MySQL test tier to CI built from the vendored schema

| | |
|---|---|
| ID | 0012 |
| Phase / milestone | Phase 1: Foundations |
| Module | platform |
| Size | M |
| Labels | arch, phase:1, module:platform, type:chore, size:M |
| Depends on | 0003, 0004, 0011 |
| Blocks | 0025, 0042, 0053, 0054, 0059, 0067, 0074, 0081, 0088, 0090 |
| Repos | mulearnbackend |

## Why

Some behaviour can only be tested on real MySQL: locks, constraints, collations, and model/DDL parity. With the vendored schema (0003), CI can build a MySQL from scratch for every pull request ([ADR-040](../adr/ADR-040-db-scripts-safety-net.md)).

## Before you start

- Issues 0003 (vendored schema) and 0011 (CI unit tier) must be merged.
- Issue 0004 must also be merged.

## What to do

1. Add a second job, `mysql`, to the `ci.yml` workflow from issue 0011:
   - a `mysql` service (matrix: `mysql:8.0` and `mysql:8.4`), with `MYSQL_DATABASE: test_mulearn` and a CI-only password;
   - a step loading `schema/latest.sql` into `test_mulearn`, then `scripts/seed-system-user.sql` (issue 0004), with `SYSTEM_ADMIN_ID` set to the seeded id in the job;
   - `scripts/test.sh --mysql` over every test root that exists: `tests/`, plus `building_blocks/` and `modules/` once issues 0014 and 0023 have created them, with `TEST_DB_HOST=127.0.0.1` and the CI password.
2. In the root `conftest.py`, for the MySQL tier only (`DATABASE_ENGINE` ends with `mysql`):
   - override pytest-django's `django_db_setup` fixture with one that does nothing, so tests use the already-loaded `test_mulearn` as it is. Without this, pytest-django creates an empty `test_test_mulearn`: every model is `managed = False` and there are no migrations, so it would have no tables;
   - add `ensure_system_user()`, which applies `scripts/seed-system-user.sql` if the system user is missing. Call it from an autouse fixture before each `mysql` test and from `pytest_sessionfinish`, because a `transaction=True` test empties every table when it ends.
3. Add `tests/mysql/test_schema_loads.py`, marked `@pytest.mark.mysql` and `@pytest.mark.django_db`. It checks that the tables `user`, `wallet` and `karma_activity_log` exist, using `connection.introspection.table_names()`.
4. State the rule in `tests/README.md`: a test that reads or writes a schema table runs on the MySQL tier and carries both markers. The SQLite tier has none of the schema's tables.

## Acceptance criteria

- [ ] Both matrix legs pass on this pull request.
- [ ] The job fails if `schema/latest.sql` fails to load.
- [ ] The guard from 0001 accepts `127.0.0.1` with `test_mulearn`.
- [ ] No `test_test_mulearn` database is created; the tests run against the loaded schema.
- [ ] A `transaction=True` test followed by another `mysql` test still finds the system user.

## How to test

Locally, with the local environment from 0004 running:

```sh
scripts/test.sh --mysql tests/mysql/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Parity tests (issues 0053 and 0054).

## Notes for reviewers

Make sure the MySQL password is a CI-only literal, not a repository secret, and that the service is reachable only from the job.
