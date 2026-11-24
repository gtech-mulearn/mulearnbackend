# Route Celery tasks to named queues and worker groups

| | |
|---|---|
| ID | 0064 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | platform |
| Size | M |
| Labels | arch, phase:3, module:platform, type:feature, size:M |
| Depends on | 0004, 0011 |
| Blocks | 0061, 0065, 0068, 0078, 0105 |
| Repos | mulearnbackend |

## Why

All Celery tasks share one default queue, so a bulk job delays OTP emails and karma awards. Routing every task to a named queue, with a worker group per queue family, isolates them ([ADR-042](../adr/ADR-042-background-work-celery.md)).

## Before you start

- Issue 0011 must be merged.
- Read `mulearnbackend/celery.py`, `CELERY_BEAT_SCHEDULE` in `mulearnbackend/settings.py`, and the modules in `mu_celery/`.
- Issue 0004 must also be merged.

## What to do

1. Declare the queues `critical`, `default`, `projections`, `notifications`, `bulk` and `integrations` in the Celery configuration.
2. Add `task_routes`, routing every task in `mu_celery/` to a queue:
   - push tasks → `notifications`;
   - organisation, learning-circle and leaderboard aggregates → `projections`;
   - media and other heavy jobs → `bulk`;
   - everything else → `default`.
3. Make sure every module with tasks is imported by the Celery app (`include=` or autodiscovery), so every beat entry resolves.
4. Create `tests/architecture/test_task_routing.py`. It fails if any registered task has no route, or any `CELERY_BEAT_SCHEDULE` entry names a task that isn't registered.
5. Update `docker-compose.local.yml` to start workers with `-Q` for all queues.

## Acceptance criteria

- [ ] The routing test passes, and fails for an unrouted test task.
- [ ] Every beat entry resolves to a registered task.
- [ ] Local workers consume every queue.

## How to test

```sh
scripts/test.sh tests/architecture/test_task_routing.py
```

## Out of scope

- Running the worker groups in deployed environments (issue 0078 for staging, issue 0105 for production).

## Notes for reviewers

Check the beat-resolution part. Some schedules may currently point at tasks no worker registers.
