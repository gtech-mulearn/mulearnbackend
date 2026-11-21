# Add model/DDL parity tests

| | |
|---|---|
| ID | 0053 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | platform |
| Size | L |
| Labels | arch, phase:3, module:platform, type:chore, size:L |
| Depends on | 0012 |
| Blocks | 0055, 0057, 0059 |
| Repos | mulearnbackend |

## Why

Every model is `managed = False`, so nothing checks that models match the real tables. Drift shows up as runtime errors. Parity tests against the vendored schema catch it in CI ([ADR-040](../adr/ADR-040-db-scripts-safety-net.md)).

## Before you start

- Issue 0012 (the MySQL tier) must be merged.

## What to do

1. Create `tests/schema/test_model_parity.py`, marked `mysql`. For every concrete model with `managed = False`, it compares the model with the CI MySQL's `information_schema`:
   - the table exists;
   - every model field's column exists;
   - nullability matches;
   - `CharField` `max_length` is not longer than the column;
   - every model `ForeignKey` has a matching database foreign key or is listed as a known difference.
2. Create `tests/schema/known_drift.toml`, listing today's differences, one per entry with an owner. Add a test that fails if an entry no longer applies, so the list only shrinks.
3. Print a readable diff on failure.

## Acceptance criteria

- [ ] The parity test passes with the known-drift list in place.
- [ ] Adding a field to a model without the column fails the test.
- [ ] Every known-drift entry names an owner.

## How to test

```sh
scripts/test.sh --mysql tests/schema/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Fixing the drift itself (each entry gets its own fix).

## Notes for reviewers

Check the comparison reads `information_schema` only and never changes the schema.
