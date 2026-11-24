# ADR-009: Selective CQRS with same-database projections

Status: Accepted (amended on 2026-11-21; merged with ADR-024)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. `organization` and `learning_circle` carry cached aggregate columns, refreshed on dev by beat jobs in `mu_celery/org_aggregates_cron.py` and `mu_celery/learning_circle_aggregates_cron.py`; leaderboards aggregate karma rows on request.

## Context

Leaderboards, ranks and dashboards aggregate large tables on public request paths. Some
organisation and learning-circle aggregates are already stored as cached columns, but nothing
refreshes them reliably.

## Options considered

- **Projection tables in MySQL fed by events,** rebuildable from the ledger.
- **A separate read store** (another database or a search engine): more infrastructure than
  today's scale needs.
- **Aggregating on every request:** cost grows with the data.

## Decision

- **Projections are MySQL tables fed by batched outbox consumers.** They can be rebuilt from the
  ledger. The first is `karma_period_total`.
- **Existing cached aggregate columns** become fed by beat jobs or consumers, each with a
  heartbeat ([ADR-042](ADR-042-background-work-celery.md)).
- **Report and admin reads** move to a read replica once [ADR-019](ADR-019-read-scaling-and-connections.md)'s trigger fires.
- There is no separate read store.

## Consequences

- Read cost is bounded and staleness is documented (about 60 seconds or less).
- Projection code has to be maintained, along with a rebuild command for each projection.

## Revisit when

- See [ADR-024](ADR-024-leaderboards-and-period-totals.md)'s triggers for sorted-set boards.

## Related ADRs

[ADR-004](ADR-004-karma-ledger.md), [ADR-019](ADR-019-read-scaling-and-connections.md), [ADR-024](ADR-024-leaderboards-and-period-totals.md), [ADR-042](ADR-042-background-work-celery.md)
