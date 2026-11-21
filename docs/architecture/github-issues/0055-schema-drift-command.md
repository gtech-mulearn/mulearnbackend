# Add a schema drift report command

| | |
|---|---|
| ID | 0055 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | platform |
| Size | M |
| Labels | arch, phase:3, module:platform, type:feature, size:M |
| Depends on | 0053 |
| Blocks | 0056 |
| Repos | mulearnbackend |

## Why

Parity tests compare models with the vendored schema. Something must also compare the vendored schema with what a live database really has, so hand-applied changes are found.

## Before you start

- Issue 0053 must be merged.

## What to do

1. In the CI MySQL job, export a JSON snapshot of the loaded schema to `schema/latest.json`: tables, columns (type, nullability, default, collation), indexes and foreign keys from `information_schema`. Commit it, and add a test that fails if it is stale.
2. Create `building_blocks/management/commands/schema_drift.py` (`manage.py schema_drift`). It reads the connected database's `information_schema`, compares it with `schema/latest.json`, and prints differences. It exits 0 when there are none and 1 when there are. It runs **read-only queries only**.
3. Add a `--format json` option, for automation.

## Acceptance criteria

- [ ] Against the local MySQL built from the vendored schema, it reports no differences.
- [ ] An extra index added locally is reported.
- [ ] The command issues no write statement.

## How to test

```sh
scripts/test.sh --mysql building_blocks/tests/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Scheduling it against production (issue 0056).

## Notes for reviewers

Check that it is read-only, because it will run against production.
