# ADR-003: One owner per table; external writers become API clients

Status: Accepted
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. The backend, the authserver, the Discord bot and the scheduler service all write overlapping tables.

## Context

The backend, the authserver, the Discord bot and the scheduler service all write overlapping
tables, and they duplicate the rules about how those tables change. A rule enforced in one writer
is not applied by another.

## Options considered

- **One owning module per table,** with every other writer calling that module's API.
- **Shared ownership with code review:** cheap, but the duplicated rules keep drifting apart.
- **Database triggers to enforce invariants:** hidden logic that Python tests can't see.

## Decision

- Every table has exactly one owning module in one deployable. The ownership catalogue is
  derived from a map of who writes each table.
- External writers (the Discord bot and the scheduler service) call `/api/v1/internal/*` with
  service credentials ([ADR-046](ADR-046-tokens-keys-service-clients.md)). They move in this order:
  1. karma: the activity log, wallet, levels and aggregates;
  2. roles;
  3. profile fields.
- The authserver writes identity tables only ([ADR-021](ADR-021-separate-identity-schema.md)).
- **Enforced by grants.** Each service connects with its own MySQL user:
  - the API;
  - workers;
  - the authserver;
  - the bot, read-only once it has moved to the API;
  - the scheduler.

  Grants are generated from an ownership manifest in `db-scripts`.
- Clarifications (2026-11-21):
  - the `contributions` module owns the `wallet` row's karma column; the coin column and the coin tables are frozen and owned by nobody new ([ADR-054](ADR-054-mucoin-external-consumer.md));
  - `system_setting` is split by key namespace;
  - feature toggles move to the flag store ([ADR-031](ADR-031-feature-flags.md)).

## Consequences

- Each rule lives in one place.
- The bot depends on backend availability. Retries and a short local queue mitigate this.
- Moving each external writer is a coordinated multi-repo release.

## Revisit when

- A new external service needs to write to the shared schema.

## Related ADRs

[ADR-004](ADR-004-karma-ledger.md), [ADR-018](ADR-018-channel-agnostic-contributions.md), [ADR-021](ADR-021-separate-identity-schema.md), [ADR-038](ADR-038-modules-own-their-tables.md), [ADR-046](ADR-046-tokens-keys-service-clients.md)
