# ADR-040: A safety net for `db-scripts` schema ownership

Status: Accepted (new on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-21)
Implementation status at dev 7fd66060: not started. There is no CI MySQL, parity test or vendored schema.

## Context

With `db-scripts` as the only schema source and `managed = False` models, models can drift from
the DDL, alter numbers collide across parallel branches, a single version number can't represent
which alters are applied, and a test suite can't build a database.

## Options considered

- **Keep the manual process, plus reviews.**
- **Patch the numeric watermark:** numbering at merge, and a monotonic version.
- **An applied-set model, plus a CI-built schema and parity tests.**
- **Generate models from the database:** this inverts ownership.

## Decision

1. **The applied-set model:**
   - New alters are named `YYYYMMDD-HHMM-<slug>.sql`, a stable id.
   - Each alter has a header: `-- id:`, `-- requires:`, `-- online:`, `-- owner:` and
     `-- expand-contract:`.
   - `dbmigrate` applies alters in id order, respecting `requires`, and records each id with its
     SHA-256.
   - Existing numbered alters keep their names and are baselined as ids.
   - The backend's `schema/REQUIRED` lists the required ids.
   - The version setting is for display only.
2. **No schema check in runtime readiness.**
   - Deploy pre-flight refuses a release whose required ids aren't all applied.
   - At boot, a new version refuses to start, so a rolling deploy halts at the canary.
   - `/healthz/ready` is process-local: shared dependencies never fail it.
3. **A production schema census comes first.** Reconcile `latest.sql` with reality, then baseline.
4. **A production apply runbook:**
   - the platform admin is the operator;
   - alters run from a bastion host, through a DDL-only database user;
   - every alter is rehearsed on a restored snapshot first.
5. **The CI schema.** A MySQL service container loads a vendored, SHA-pinned `latest.sql`,
   refreshed by a bot pull request.
6. **Parity tests**, for every unmanaged model:
   - tables and columns, with type, length and nullability;
   - foreign-key delete rules;
   - unique keys and indexes;
   - every enum, case-sensitive.

   Known drift sits in an allowlist that may only shrink.
7. **A smoke test for other services' SQL.** Their SELECT statements run as `EXPLAIN` against the
   CI database.
8. **Nightly drift detection** diffs production `information_schema` against the CI-built schema,
   and opens a ticket on any difference.
9. **Expand/contract rules:**
   - expand alters are additive and online;
   - code ships after its alter;
   - a contract alter runs only after no deployed code references the column.
10. **Two test tiers, guarded.** SQLite in memory for unit tests; MySQL built from `latest.sql`
    for integration tests, which refuse any host other than the CI or compose container and any
    database name that neither starts with `test_` nor ends with `_test`.

### Refinements (2026-11-21)

- The migration ledger's id column is `VARCHAR(64)` `ascii_bin`, wide enough for timestamped ids, and is widened before the first baseline runs.
- New alter ids form an explicit `requires:` chain.
- A separate `/healthz/deps` endpoint reports dependency status to operators and requires a token header; `/healthz/ready` stays process-local.

## Consequences

- Drift and collisions are caught in CI, not in production.
- Contributors run the MySQL tier locally with one command.

## Revisit when

- More than one drift incident happens in a quarter despite the gates. Then generate
  `latest.sql`.

## Related ADRs

[ADR-002](ADR-002-mysql-8-4-lts.md), [ADR-014](ADR-014-db-scripts-single-schema-source.md), [ADR-021](ADR-021-separate-identity-schema.md), [ADR-049](ADR-049-deployment-platform-and-dr.md), [ADR-051](ADR-051-toolchain.md)
