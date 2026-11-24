# ADR-014: `db-scripts` is the permanent, single source of schema

Status: Accepted
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: partly in place. `db-scripts` already owns the schema and every model is `managed = False`; the migration runner with an applied-scripts record, the `MIGRATION_MODULES` guard and the vendored schema copy do not exist yet.

## Context

Several services share one MySQL cluster. Large tables need deliberate online-DDL strategies,
and schema changes deserve their own review. Keeping schema in each service's framework
migrations would split the history, and would weaken control over how DDL runs against big
tables.

## Options considered

- **Versioned SQL in `db-scripts`, applied by its runner,** with no framework migrations.
- **Django-managed migrations per module:** rejected. The schema serves several services, online
  DDL is harder to control, and review would be split.
- **Flyway or Atlas as the runner:** acceptable later. The principle stays the same.

## Decision

- All schema, core and identity, is versioned SQL in `db-scripts`, applied by its migration runner
  (`dbmigrate`) with a checksummed record of applied scripts.
- `db-scripts` is a private repository. A schema-only copy of its `latest.sql` (DDL only, with no
  data and no comments) is vendored into this repository as `schema/latest.sql`, with the source commit in `schema/SOURCE`. A maintainer
  refreshes it after each alter merges. It feeds local development and the CI MySQL tier.
- This repository has no Django migrations. `MIGRATION_MODULES` maps every app to `None`, and a
  test fails if a `migrations` package appears.
- Models are `managed = False`. Changing a model requires the matching SQL.
- **Third-party DDL is generated once and committed to `db-scripts`.** This includes the
  authserver's OAuth provider tables.
- The safety net that makes this ownership safe is [ADR-040](ADR-040-db-scripts-safety-net.md).

## Consequences

- One reviewed history for every service that touches the schema.
- A schema change is a pull request in two repositories, and the SQL merges and is applied
  first. Contributors without access to `db-scripts` put the exact DDL in their backend issue or
  pull request; a maintainer writes and applies the alter.
- Contributors write SQL instead of generating it, helped by a template and a header linter.

## Revisit when

- Drift incidents continue despite [ADR-040](ADR-040-db-scripts-safety-net.md)'s gates.

## Related ADRs

[ADR-002](ADR-002-mysql-8-4-lts.md), [ADR-021](ADR-021-separate-identity-schema.md), [ADR-038](ADR-038-modules-own-their-tables.md), [ADR-040](ADR-040-db-scripts-safety-net.md)
