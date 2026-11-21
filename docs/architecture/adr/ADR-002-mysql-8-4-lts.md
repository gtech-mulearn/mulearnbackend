# ADR-002: Stay on MySQL; upgrade to 8.4 LTS

Status: Accepted (reviewed on 2026-11-21: the upgrade moves earlier)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. The database runs MySQL 8.0.

## Context

- Several services write the same MySQL schema through different drivers: Django, a NestJS
  service and a Python bot.
- The schema has about 170 tables and about 450 foreign keys, and it is managed by
  versioned SQL in `db-scripts`.
- Some behaviour depends on MySQL collations.
- MySQL 8.0 has left standard support on RDS, so staying on it now costs Extended Support fees.
- Django 6.1 and later require MySQL 8.4 or newer.
- MySQL LTS series can't be skipped, so the path is 8.0 → 8.4 → the next LTS.

## Options considered

- **Stay on 8.0 with Extended Support:** cost rises, and Django 6.1+ stays out of reach.
- **Upgrade to 8.4 LTS now.**
- **Migrate to PostgreSQL:** better pooling, partial indexes and transactional DDL, but the cost
  is very high:
  - every foreign key and table moves;
  - raw SQL in other services has to be rewritten;
  - the db-scripts tooling has to be rebuilt;
  - collation-dependent behaviour changes meaning.
- **Aurora MySQL 3:** still 8.0-compatible, so it only defers the same upgrade.

## Decision

Stay on MySQL, and upgrade to 8.4 LTS using an RDS blue/green deployment:

1. Run pre-flight checks against the production schema:
   - no `utf8mb3` tables;
   - no foreign keys on non-unique keys;
   - no FLOAT auto-increment columns;
   - an inventory of accounts using the legacy authentication plugin.
2. Rehearse the upgrade on a restored production snapshot.
3. On the green environment, smoke-test every service that connects, including each driver's
   authentication-plugin and TLS support.
4. Keep the legacy authentication plugin enabled until every client is verified.
5. Run the CI schema-parity suite on 8.4 ([ADR-040](ADR-040-db-scripts-safety-net.md)).

Upgrade outside the academic exam period.

## Consequences

- No database conversion programme.
- Collation pitfalls remain, and are handled in code: never decide identity by SQL string
  equality.
- Partial indexes are not available; use the generated-column workaround.

## Revisit when

Reconsider PostgreSQL only when all three hold:
1. All external writers have moved behind the API.
2. There is a measured need (partial or expression indexes, transactional DDL, or pooling) that
   blocks releases at least twice a quarter.
3. A migration estimate comes in under one quarter of team time.

## Related ADRs

[ADR-003](ADR-003-one-owner-per-table.md), [ADR-014](ADR-014-db-scripts-single-schema-source.md), [ADR-040](ADR-040-db-scripts-safety-net.md), [ADR-050](ADR-050-platform-versions.md)
