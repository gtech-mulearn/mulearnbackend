# ADR-022: Transactions never cross module boundaries

Status: Accepted (amended on 2026-11-21; the enforced rules are in ADR-041)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. Legacy views often write several areas' tables inside one transaction.

## Context

A module command running inside another module's transaction couples modules at the lock and
transaction level, and that blocks extraction.

## Options considered

- **Strict events only, everywhere:** too rigid where a caller needs an answer now.
- **Events by default; synchronous commands each in their own transaction**.
- **Shared transactions across modules:** couples everything.

## Decision

- A service's transaction touches only its own module's tables, plus the outbox.
- Other modules react to its events and apply them idempotently.
- [ADR-041](ADR-041-transactions-and-consistency.md) refines and enforces this:
  - an `@command(owner=...)` guard detects nested cross-module transactions;
  - synchronous cross-module commands are allowed when the caller needs an answer now, and each
    runs in its own transaction;
  - legacy callers are allowlisted until their module cuts over.

## Consequences

- Cross-module effects arrive seconds later, and the UI shows "pending" until then.
- Lock scopes shrink, and the module graph stays a directed acyclic graph.

## Revisit when

- See [ADR-041](ADR-041-transactions-and-consistency.md).

## Related ADRs

[ADR-005](ADR-005-transactional-outbox.md), [ADR-041](ADR-041-transactions-and-consistency.md)
