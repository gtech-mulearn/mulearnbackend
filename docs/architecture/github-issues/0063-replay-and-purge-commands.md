# Add dead-letter replay and outbox purge commands

| | |
|---|---|
| ID | 0063 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | building_blocks |
| Size | M |
| Labels | arch, phase:3, module:building_blocks, type:feature, size:M |
| Depends on | 0062 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

After a bug is fixed, parked deliveries must be re-sent. Old outbox and inbox rows must be cleaned up so the tables don't grow without bound.

## Before you start

- Issue 0062 must be merged.

## What to do

1. Create `building_blocks/management/commands/replay_dead_letters.py` (`--consumer <name>`, `--id <n>`, `--dry-run`). It re-queues open dead letters to their consumer and marks them resolved when they succeed.
2. Create `building_blocks/management/commands/purge_messaging.py`. It deletes published outbox rows and inbox rows older than 30 days, in batches of 5,000 with a short sleep between batches.
3. Schedule the purge daily on the `bulk` queue, through the beat schedule.
4. Add tests for both commands.

## Acceptance criteria

- [ ] A replayed dead letter runs its consumer once and is marked resolved.
- [ ] The purge never deletes an unpublished outbox row or an inbox row younger than 30 days.

## How to test

```sh
scripts/test.sh --mysql building_blocks/tests/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Alerting on dead letters. That comes with the dashboards (issue 0048) and the first consumers.

## Notes for reviewers

Check the purge's `WHERE` clauses carefully.
