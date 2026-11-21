# ADR-021: A separate identity schema and database user

Status: Accepted (amended on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. The authserver reads and writes tables in the same schema as the backend, including `user`.

## Context

"Separate" must mean separate data, not only a separate process. A shared `user` table makes the
identity split a distributed monolith.

## Options considered

- **A separate schema and database user for identity,** linked by user UUID only.
- **Shared tables with code ownership:** the two systems stay coupled at the data level.

## Decision

- **Step 0:** bring every identity table's DDL into `db-scripts` first. This
  includes federated identities and the OAuth provider tables.
- The identity system owns its own schema, with its own database user and keys.
- No cross-schema reads, joins or foreign keys.
- The two systems are linked only by the user UUID.
- Data flows one way, through provisioning calls and signed events ([ADR-046](ADR-046-tokens-keys-service-clients.md)).

## Consequences

- Each system can scale, be secured and later move to its own instance independently.
- A staged migration, with a short period in which some identity columns stay on `user`.

## Revisit when

- Identity needs its own database instance.

## Related ADRs

[ADR-008](ADR-008-authserver-separate-idp.md), [ADR-014](ADR-014-db-scripts-single-schema-source.md), [ADR-040](ADR-040-db-scripts-safety-net.md), [ADR-046](ADR-046-tokens-keys-service-clients.md)
