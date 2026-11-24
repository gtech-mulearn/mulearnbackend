# Create the feature flag tables

| | |
|---|---|
| ID | 0073 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | building_blocks |
| Size | S |
| Labels | arch, phase:3, module:building_blocks, type:feature, size:S, maintainer-only, repo:db-scripts, needs-db-change |
| Depends on | 0049 |
| Blocks | 0074 |
| Repos | db-scripts |

## Why

Feature flags today are scattered across settings rows, configuration tables and environment switches. One persisted, audited store replaces them ([ADR-031](../adr/ADR-031-feature-flags.md)).

## Before you start

- Maintainer-only: the work happens in the private `db-scripts` repository.
- Read [Where the schema lives, and how it changes](../06-data-and-schema.md#where-the-schema-lives-and-how-it-changes).
- Issue 0049 (stable alter ids) must be merged.

## What to do

1. Write one expand alter in `db-scripts`, with a stable id and the standard header (`-- id:`, `-- requires:`, `-- online: yes`, `-- owner:`, `-- expand-contract: expand`), containing:

   ```sql
   CREATE TABLE feature_flag (
     flag_key VARCHAR(100) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
     kind ENUM('release','ops','kill','shadow','experiment') NOT NULL,
     enabled TINYINT(1) NOT NULL DEFAULT 0,
     rollout_percent TINYINT UNSIGNED NOT NULL DEFAULT 0,
     owner VARCHAR(64) NOT NULL,
     expires_at DATETIME(6) NULL,
     flip_by DATETIME(6) NULL,
     updated_by VARCHAR(36) NULL,
     updated_at DATETIME(6) NOT NULL
   );
   CREATE TABLE feature_flag_change (
     id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
     flag_key VARCHAR(100) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
     before_state JSON NULL,
     after_state JSON NOT NULL,
     actor VARCHAR(36) NOT NULL,
     reason VARCHAR(255) NOT NULL,
     changed_at DATETIME(6) NOT NULL,
     KEY idx_feature_flag_change_key (flag_key, changed_at)
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
