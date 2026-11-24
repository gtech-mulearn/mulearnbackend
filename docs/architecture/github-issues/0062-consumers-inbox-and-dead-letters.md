# Add consumers with inbox de-duplication, retries and dead letters

| | |
|---|---|
| ID | 0062 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | building_blocks |
| Size | L |
| Labels | arch, phase:3, module:building_blocks, type:feature, size:L, core-review |
| Depends on | 0061 |
| Blocks | 0063, 0069 |
| Repos | mulearnbackend |

## Why

Delivery is at least once, so consumers must make redelivery harmless, retry failures and park what can't be processed ([05-events-and-background-work.md](../05-events-and-background-work.md#how-an-event-travels)).

## Before you start

- Issue 0061 must be merged.

## What to do

1. Create `building_blocks/messaging/registry.py` with `subscribe(event_cls, accepts=None)`, which maps event types (with accepted versions) to consumers, and `consumers_for(event_type: str, version: int) -> list[str]`, which `dispatch` uses. Keys are the short `EVENT_TYPE` (issue 0060).
2. Create `building_blocks/messaging/consumer.py` with `consumer(name: str, queue: str, external: bool = False)`. It registers a Celery task per consumer.
   - **The `dispatch` task** (called by the relay) reads the short type and version from the envelope's `type` with `parse_type` (issue 0060), and fans the envelope out to `consumers_for` them.
   - **A delivery of an unaccepted version** goes straight to `dead_letter` and raises an alert metric, without calling the handler.
   - **Non-external consumers** run the handler inside a transaction that first inserts `inbox_record (consumer, event_id)`. A duplicate key means "already processed", and the delivery is skipped.
   - **External consumers** run the handler outside any transaction, and record the inbox row only after success.
   - **Failures** retry with jittered exponential backoff, up to 8 attempts. After the last, a `DeadLetter` row is written with the error.
3. Add MySQL-tier tests:
   - the same envelope delivered twice runs the handler once;
   - an unknown version is dead-lettered;
   - a handler that always fails ends in a dead letter after the configured attempts.

## Acceptance criteria

- [ ] All tests pass.
- [ ] A consumer's work and its inbox row commit or roll back together.
- [ ] Dead letters contain the full envelope and the last error.

## How to test

```sh
scripts/test.sh --mysql building_blocks/tests/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Replay commands (issue 0063).
- Webhooks to external consumers (on hold with the μCoin integration, [ADR-054](../adr/ADR-054-mucoin-external-consumer.md)).

## Notes for reviewers

Check the inbox insert happens in the same transaction as the handler for non-external consumers.
