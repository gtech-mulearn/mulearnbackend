# ADR-053: Business calendar and money types

Status: Accepted (new on 2026-11-21; money-column migration deferred)
Date: 2026-11-21 (first accepted 2026-11-21)
Implementation status at dev 7fd66060: not started.

## Context

Data is stored in UTC, but the business runs on Indian Standard Time: midnight IST is 18:30 UTC on
the previous day. Monthly boundaries computed naively in UTC put awards in the wrong month. Some
existing money and coin columns are floating point (the coin columns are frozen, [ADR-054](ADR-054-mucoin-external-consumer.md)).

## Options considered

- **One clock and business-calendar helper, used by every period query.**
- **Per-feature date arithmetic:** the same bug recurs.

## Decision

- **`building_blocks/clock`** provides:
  - `now()`, an aware UTC datetime;
  - `BUSINESS_TZ = Asia/Kolkata`;
  - `period_bounds(kind, at, tz=BUSINESS_TZ)` for day, week, month and year.

  All period queries use these bounds. Academic terms become chapter data later.
- **Tests** cover 18:29 and 18:30 UTC on month ends, and the roll from December to January.
- **Money** is stored as integer minor units (paise, BIGINT) in new payment tables, from the
  first payments change.
- **Migrating existing floating-point columns** to DECIMAL or INT with checks is deferred.

### Refinements (2026-11-21)

- Durations are exact `timedelta`s ("older than 30 days"); business periods ("this month", "tomorrow") come from `period_bounds` in IST. The two are never mixed.
- The ledger's `period` uses the same calendar ([ADR-004](ADR-004-karma-ledger.md)).

## Consequences

- Monthly boards and reports agree with what users see in IST.

## Revisit when

- Webhook-driven payments or refunds are built (then migrate the money columns), or a second state
  with a different academic calendar is onboarded.

## Related ADRs

[ADR-024](ADR-024-leaderboards-and-period-totals.md), [ADR-028](ADR-028-chapter-materialised-paths.md), [ADR-041](ADR-041-transactions-and-consistency.md)
