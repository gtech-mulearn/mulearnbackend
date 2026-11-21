# ADR-024: Leaderboards from durable period totals; sorted sets on trigger

Status: Accepted (amended on 2026-11-21; sorted sets deferred to a trigger)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. `api/leaderboard/` aggregates karma rows; on dev, `mu_celery/leaderboard_cron.py` refreshes cached boards twice a day.

## Context

Leaderboards and ranks are read far more often than karma is awarded. At current award rates,
maintaining a durable totals table is well within the primary's capacity.

## Options considered

- **Durable `karma_period_total` rows fed by a batched consumer; Redis sorted sets later.**
- **Redis sorted sets now:** Redis becomes important state before the load needs it.
- **Aggregate on read:** cost grows with the data.

## Decision

- An outbox consumer maintains `karma_period_total` by recomputing the affected learner's totals
  for the period from the ledger, under a per-learner lock. Unlike a delta, a recompute cannot
  count an entry twice when it is delivered after a rebuild. The rows are rebuildable from the
  ledger.
- Totals carry `member_path` and `task_scope_path` from day one, so chapter boards need no
  rebuild later ([ADR-028](ADR-028-chapter-materialised-paths.md), [ADR-029](ADR-029-board-definitions.md)).
- Redis sorted sets, rebuilt from the totals, are added when the trigger fires. The totals stay
  the rebuildable source either way.

## Consequences

- One source of truth for boards, and no new state store.
- Boards are slightly stale (micro-batch interval).

## Revisit when

- Board p95 exceeds 150 ms with indexed totals, awards exceed 50 per second sustained, or a
  board passes 500,000 members.

## Related ADRs

[ADR-004](ADR-004-karma-ledger.md), [ADR-009](ADR-009-selective-cqrs-projections.md), [ADR-029](ADR-029-board-definitions.md), [ADR-030](ADR-030-leaderboard-algorithms.md), [ADR-043](ADR-043-redis-cache-and-state.md)
