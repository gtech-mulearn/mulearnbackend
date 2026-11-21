# ADR-032: Audit trail and retention

Status: Accepted (amended on 2026-11-21: scaled down; tamper evidence deferred)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. Several features write `system_action_log` rows directly.

## Context

Karma, grants, payments and staff access to personal data need records that survive disputes,
privacy obligations and investigations. Several features write ad-hoc action logs today.

## Options considered

- **One INSERT-only `audit_event` table, written in the business transaction.**
- **Hash chains, signed checkpoints and WORM storage now:** strong guarantees, but more to run
  than current obligations need.
- **An external ledger service:** a new processor and residency questions.

## Decision

**Now:**
- One INSERT-only `audit_event` table in the core schema, written by `building_blocks/audit` in
  the business transaction.
- It absorbs the existing system action log.
- The application's database user has only INSERT and SELECT on it.
- Payloads carry no personal data, only UUIDs ([ADR-052](ADR-052-privacy-minors-erasure.md)).

**Deferred:** SHA-256 hash chains, signed checkpoints and S3 Object Lock.

## Consequences

- One place to answer "who did what, when".
- History isn't provably tamper-evident until the deferred work lands.

## Revisit when

- The organisation is notified as a Significant Data Fiduciary, counsel advises it, or a dispute
  requires provable history.

## Related ADRs

[ADR-007](ADR-007-scoped-grants-and-policies.md), [ADR-052](ADR-052-privacy-minors-erasure.md)
