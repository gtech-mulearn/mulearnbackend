# ADR-015: Keep UUID `VARCHAR(36)` keys; BIGINT for new append-heavy tables; UUIDv7 for new ids

Status: Accepted (amended on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: the existing keys are as described (mostly `CharField(max_length=36)` UUID strings). The UUIDv7 helper and the `ascii_bin` rule for new columns are not started.

## Context

Primary and foreign keys across the schema are UUID strings in `VARCHAR(36)`, referenced by
hundreds of foreign-key columns. Converting them all has no incremental path. Sequential
identifiers in URLs let anyone enumerate records.

## Options considered

- **Keep `VARCHAR(36)`; use BIGINT surrogates for new append-heavy tables; UUIDv7 for new ids.**
- **`BINARY(16)` everywhere:** touches every foreign key for a constant-factor gain, and breaks
  the language-neutral contract that uses `CHAR(36)`.
- **A BIGINT surrogate on every table, plus a public UUID:** a full-schema migration.

## Decision

- Existing UUID keys stay as they are. New ids are UUIDv7 (`building_blocks.ids`).
- New append-heavy tables (ledgers, outbox, logs) may use BIGINT primary keys.
- **New key and reference columns** (idempotency keys, source references, chapter paths) use the
  `ascii_bin` collation, so comparisons are exact.
- **Public and internal ids are separate:**
  - BIGINT surrogate keys never appear in URLs or payloads;
  - public references are UUIDs, or `muid` for people;
  - enumerable sequential ids are never exposed.

## Consequences

- No big-bang schema change.
- Index overhead from string keys is accepted.

## Revisit when

- Indexes on user foreign-key columns exceed 30% of the InnoDB buffer pool.

## Related ADRs

[ADR-004](ADR-004-karma-ledger.md), [ADR-028](ADR-028-chapter-materialised-paths.md), [ADR-040](ADR-040-db-scripts-safety-net.md)
