# ADR-033: SLOs and burn-rate alerting for a volunteer team

Status: Accepted (amended on 2026-11-21: simplified)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. There are no SLOs, burn-rate alerts or bot heartbeat.

## Context

A part-time team in one time zone needs every page to mean real user harm. Static thresholds are
noisy and blind to slow burns.

## Options considered

- **A small set of SLOs with burn-rate alerts and a paging policy.**
- **Static thresholds:** noisy.
- **A full error-budget policy with generated rules from day one:** more process than the team
  can sustain at first.

## Decision

**First SLOs, over 30-day windows:**

| SLO | Target | Alerting |
|---|---|---|
| API availability (non-5xx) | 99.5% | Pages on burn rate |
| Award latency, approval → ledger | p95 ≤ 60 s | Pages |
| Signup success | ≥ 99% | Ticket |
| Bot task-channel processing | events processed within 10 min of channel activity | Page by day, ops channel at night |
| Appraiser-queue age | oldest < 48 h | Ticket to community operations |
| Outbox lag (oldest unpublished) | < 5 min | Pages |
| Scheduled-run heartbeats | ≤ 2 × interval | Ticket |
| Ledger reconciliation drift | 0 | Ticket during migration; page after a module's cut-over |

**Paging policy:**
- Pages go out only 07:00–23:00 IST, with a business-hours response target.
- Out of hours, alerts go to the ops channel.
- There is one named escalation person for the ledger and one for authentication.
- Every page has a runbook before it goes live.

Generated rules and a formal error-budget policy come later.

## Consequences

- Fewer pages, each of them meaningful.
- Out-of-hours incidents wait until morning unless someone is watching the ops channel.

## Revisit when

- More than 3 pages a week aren't user-harmful.

## Related ADRs

[ADR-004](ADR-004-karma-ledger.md), [ADR-012](ADR-012-opentelemetry-sentry-json-logs.md), [ADR-018](ADR-018-channel-agnostic-contributions.md), [ADR-042](ADR-042-background-work-celery.md)
