# ADR-042: Background work: Celery with routed queues and exactly-once schedule slots

Status: Accepted (new on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-21)
Implementation status at dev 7fd66060: not started. All tasks in `mu_celery/` go to the default queue (no routes); one beat runs the 14 entries in `CELERY_BEAT_SCHEDULE`.

## Context

Background work shares one queue today, so a bulk job can delay OTP emails and karma awards.
Schedules must run exactly once per slot, even if two beat processes start by mistake. Django's
built-in task framework doesn't yet have production-grade backends. A separate scheduler service
also runs jobs against the shared schema.

## Options considered

- **Celery, configured properly.**
- **Django's task framework with a third-party database backend:** not yet production-grade.
- **Dramatiq or RQ:** a migration with no clear gain.

## Decision

1. **Queues:**
   - `critical`: awards from events, payment confirmation, verification email;
   - `default`;
   - `notifications`;
   - `integrations`;
   - `bulk`: imports, exports and backfills;
   - `projections`.

   Every task is routed.
2. **Worker groups:**

   | Group | Queues | Notes |
   |---|---|---|
   | `worker-fast` | `critical`, `default`, `projections` | priority order, so `critical` drains first |
   | `worker-notify` | `notifications` | isolates bursty campaigns |
   | `worker-bulk` | `bulk`, `integrations` | low concurrency, memory-capped |

3. **The task contract:**
   - New tasks declare whether they are idempotent.
   - Idempotent tasks use `acks_late` and `reject_on_worker_lost`.
   - Default limits are soft 240 s and hard 300 s.
   - Retries use backoff with jitter.
   - A task must finish within the broker's visibility timeout, or be chunked.
   - No `eta` or `countdown` beyond half the visibility timeout. Longer delays are database rows
     released by a beat sweep.
4. **At most one run per slot.**
   - Every scheduled task first claims `(schedule_name, slot_start)` by inserting into a UNIQUE
     `schedule_run` table, so a duplicate beat is a no-op.
   - The same row is the schedule's heartbeat.
   - A CI test asserts that every beat entry resolves to a registered task.
5. **Schedules are enabled one at a time, behind flags,** after their backlogs are checked.
6. **The scheduler service is fixed in place now and absorbed later.**
   - Now: its jobs fail closed, run per-user updates transactionally with idempotency checks, and
     send email only after commit.
   - Later, its jobs move into module beat tasks.

### Refinements (2026-11-21)

- The decorator is `@scheduled(name, *, every, crontab=None)`, placed directly under `@shared_task`. `name` must equal the task's name; `every` is the slot length (daily slots start at midnight IST); `crontab` says when beat fires, in UTC. `build_beat_schedule()` collects the declarations, so there is no second list.
- Daily purges remove expired idempotency records, inbox rows and published outbox rows older than 30 days, and `schedule_run` rows older than 90 days.
- Schedule flags are off by default in production ([ADR-031](ADR-031-feature-flags.md)).

## Consequences

- Critical work is isolated from bulk work.
- Duplicate schedule runs become impossible.

## Revisit when

- Django's task framework and a database backend reach a stable 1.0. New tasks may then use the
  `@task` API with a Celery backend.

## Related ADRs

[ADR-005](ADR-005-transactional-outbox.md), [ADR-023](ADR-023-one-image-several-roles.md), [ADR-033](ADR-033-slos-and-burn-rate-alerts.md), [ADR-043](ADR-043-redis-cache-and-state.md), [ADR-047](ADR-047-notification-pipeline.md)
