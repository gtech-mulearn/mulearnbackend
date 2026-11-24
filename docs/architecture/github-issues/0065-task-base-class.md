# Add a task base with time limits, acks_late and backoff

| | |
|---|---|
| ID | 0065 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | building_blocks |
| Size | M |
| Labels | arch, phase:3, module:building_blocks, type:feature, size:M |
| Depends on | 0064 |
| Blocks | 0067, 0069 |
| Repos | mulearnbackend |

## Why

Every task can run twice, so each needs time limits, safe acknowledgement and bounded retries. A long `eta` or `countdown` beyond the broker's visibility timeout makes Redis redeliver the task ([ADR-042](../adr/ADR-042-background-work-celery.md)).

## Before you start

- Issue 0064 must be merged.

## What to do

1. Create `building_blocks/tasks.py` with a Celery `Task` subclass `MuTask`:
   - `acks_late = True`, `reject_on_worker_lost = True`;
   - default `soft_time_limit` and `time_limit` per queue (for example 30/60 s on `critical`, 1,500/1,800 s on `bulk`);
   - `autoretry_for` the exceptions a task declares, with jittered exponential backoff up to 5 retries.
2. Add a decorator `mu_task(queue: str, **opts)` that applies `MuTask` and the route.
3. Make `apply_async` on a `MuTask` raise when `eta` or `countdown` is further away than the broker's `visibility_timeout`.
4. Add tests for the defaults, the retry policy and the ETA guard.

## Acceptance criteria

- [ ] All tests pass.
- [ ] A task scheduled with a 10-hour countdown raises instead of queueing.

## How to test

```sh
scripts/test.sh building_blocks/tests/
```

## Out of scope

- Converting existing tasks. They move as their modules do.

## Notes for reviewers

Check the visibility-timeout guard reads the configured value, not a constant.
