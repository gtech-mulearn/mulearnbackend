# Add enum parity tests

| | |
|---|---|
| ID | 0054 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | platform |
| Size | M |
| Labels | arch, phase:3, module:platform, type:chore, size:M |
| Depends on | 0012 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

MySQL enums compare case-insensitively, but Python doesn't. A Django `choices` value whose case differs from the database `ENUM` value breaks comparisons silently, and a value missing from the `ENUM` fails on write. Enum parity tests catch both.

## Before you start

- Issue 0012 must be merged.

## What to do

1. Create `tests/schema/test_enum_parity.py`, marked `mysql`. For every model field with `choices` mapped to an `ENUM` column, it compares the set of choice values with the column's `ENUM` values **case-sensitively**.
2. Record existing mismatches in `tests/schema/known_drift.toml` with owners.
3. Report case-only mismatches separately, because they are the dangerous ones.

## Acceptance criteria

- [ ] It covers every `ENUM` column that a model maps.
- [ ] A choice missing from the `ENUM` fails, and a case-only mismatch fails with a specific message.

## How to test

```sh
scripts/test.sh --mysql tests/schema/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Changing enum values.

## Notes for reviewers

Enum values are part of the API for some endpoints. Fixes need care, so they are separate issues.
