# Create the service_client table

| | |
|---|---|
| ID | 0089 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | building_blocks |
| Size | S |
| Labels | arch, phase:4, module:building_blocks, type:feature, size:S, maintainer-only, repo:db-scripts, needs-db-change |
| Depends on | 0049 |
| Blocks | 0090 |
| Repos | db-scripts |

## Why

Machine callers such as the Discord bot need their own credentials, scopes and quotas, stored hashed ([ADR-046](../adr/ADR-046-tokens-keys-service-clients.md)).

## Before you start

- Maintainer-only: the work happens in the private `db-scripts` repository.
- Read [Where the schema lives, and how it changes](../06-data-and-schema.md#where-the-schema-lives-and-how-it-changes).
- Issue 0049 (stable alter ids) must be merged.

## What to do

1. Write one expand alter in `db-scripts`, with a stable id and the standard header (`-- id:`, `-- requires:`, `-- online: yes`, `-- owner:`, `-- expand-contract: expand`), containing:

   ```sql
   CREATE TABLE service_client (
     id VARCHAR(36) NOT NULL PRIMARY KEY,
     name VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
     secret_hash VARCHAR(255) NOT NULL,
     previous_secret_hash VARCHAR(255) NULL,
     previous_valid_until DATETIME(6) NULL,
     scopes JSON NOT NULL,
     act_as JSON NOT NULL,
     quota_per_minute INT NOT NULL DEFAULT 600,
     active TINYINT(1) NOT NULL DEFAULT 1,
     created_at DATETIME(6) NOT NULL,
     updated_at DATETIME(6) NOT NULL,
     UNIQUE KEY uq_service_client_name (name)
   );
   ```
2. Apply it to the shared environments through the migration runner after review: `dev`, then `staging`, then `production`.
3. Refresh the backend's `schema/latest.sql`, following the routine in the issues README.

## Acceptance criteria

- [ ] The alter is idempotent.
- [ ] It loads into a fresh `mysql:8.0` and `mysql:8.4` from `latest.sql`.
- [ ] `schema/latest.sql` in the backend contains the new tables.

## How to test

Load `latest.sql` into a throwaway local MySQL container, run `SHOW CREATE TABLE` for each new table, and paste the output.

## Out of scope

- The backend models (the next issue in the chain).

## Notes for reviewers

Check the key columns are `ascii_bin` and every natural key has a `UNIQUE` constraint.
