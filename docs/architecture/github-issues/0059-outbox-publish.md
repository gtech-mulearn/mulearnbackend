# Add the outbox models and outbox.publish_raw

| | |
|---|---|
| ID | 0059 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | building_blocks |
| Size | M |
| Labels | arch, phase:3, module:building_blocks, type:feature, size:M, core-review, needs-db-change |
| Depends on | 0012, 0015, 0021, 0053, 0058 |
| Blocks | 0060, 0061, 0069, 0084 |
| Repos | mulearnbackend |

## Why

Events must exist if and only if the change they describe commits. Writing them to an outbox table in the same transaction is how ([ADR-005](../adr/ADR-005-transactional-outbox.md)).

## Before you start

- Issues 0015 (ids), 0021 (`@command`) and 0058 (the tables, applied) must be merged.
- Issues 0012 and 0053 must also be merged.

## What to do

1. Create `building_blocks/messaging/models.py` with `managed = False` models `OutboxEvent`, `InboxRecord`, `DeadLetter` and `IdempotencyRecord`. They mirror issue 0058's DDL exactly; the parity test (0053) covers them.
2. Create `building_blocks/messaging/outbox.py` with `publish_raw(*, type: str, source: str, subject: str, envelope: dict) -> None`:
   - it raises if not inside `transaction.atomic()`;
   - it inserts one `OutboxEvent`, using the envelope's `id` as `event_id`.
3. Add tests in `building_blocks/tests/mysql/test_outbox.py` (the outbox table exists only on the MySQL tier):
   - a rollback leaves no row;
   - a commit leaves one;
   - calling outside a transaction raises. Any `django_db` test already runs inside a transaction, so this one uses `transaction=True`.

## Acceptance criteria

- [ ] All tests pass on the MySQL tier.
- [ ] The parity test passes for the new models.

## How to test

```sh
scripts/test.sh --mysql building_blocks/tests/mysql/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- The envelope builder (issue 0060).
- The relay (issue 0061).

## Notes for reviewers

Check that publishing is impossible outside a transaction.
