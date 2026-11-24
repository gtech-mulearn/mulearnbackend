# Claim each scheduled slot once and record heartbeats

| | |
|---|---|
| ID | 0067 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | building_blocks |
| Size | M |
| Labels | arch, phase:3, module:building_blocks, type:feature, size:M, needs-db-change |
| Depends on | 0012, 0065, 0066 |
| Blocks | 0100 |
| Repos | mulearnbackend |

## Why

Two beats, for example after a failover, would run every job twice. Claiming `(schedule, slot)` first makes each run happen once, and the claim doubles as the heartbeat ([05-events-and-background-work.md](../05-events-and-background-work.md#queues-and-workers)).

## Before you start

- Issues 0065 and 0066 (applied) must be merged.
- Issue 0012 must also be merged.

## What to do

1. Add a `managed = False` model `ScheduleRun` in `building_blocks/models.py`, matching issue 0066.
2. Add a decorator `scheduled(name: str)`. Before the task body runs, it inserts `(name, slot_start)`, where `slot_start` is the beat's scheduled time truncated to the minute. A duplicate key means another run claimed the slot, so the task returns without running. It records `succeeded` or `failed` with `finished_at`.
3. Wrap every entry in `CELERY_BEAT_SCHEDULE` with it.
4. Export a metric: seconds since the last success, per schedule.
5. Add MySQL-tier tests: two runs of the same slot run the body once, and a failure is recorded.

## Acceptance criteria

- [ ] Two beats running at once don't run any job twice: simulate it in a test.
- [ ] Every schedule records its runs.

## How to test

```sh
scripts/test.sh --mysql building_blocks/tests/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Alerting on missed heartbeats (dashboards issue).

## Notes for reviewers

Check that the slot is derived from the scheduled time, not the start time, so a late start still dedupes.
