# Create the schedule_run table

| | |
|---|---|
| ID | 0066 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | building_blocks |
| Size | S |
| Labels | arch, phase:3, module:building_blocks, type:feature, size:S, maintainer-only, repo:db-scripts, needs-db-change |
| Depends on | 0049 |
| Blocks | 0067 |
| Repos | db-scripts |

## Why

Scheduled jobs must run once per slot, even if two beats run after a failover, and each run should leave a heartbeat ([ADR-042](../adr/ADR-042-background-work-celery.md)).

## Before you start

- Maintainer-only: the work happens in the private `db-scripts` repository.
- Read [Where the schema lives, and how it changes](../06-data-and-schema.md#where-the-schema-lives-and-how-it-changes).
- Issue 0049 (stable alter ids) must be merged.

## What to do

1. Write one expand alter in `db-scripts`, with a stable id and the standard header (`-- id:`, `-- requires:`, `-- online: yes`, `-- owner:`, `-- expand-contract: expand`), containing:

   ```sql
   CREATE TABLE schedule_run (
     schedule VARCHAR(100) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
     slot_start DATETIME(6) NOT NULL,
     claimed_by VARCHAR(191) NOT NULL,
     claimed_at DATETIME(6) NOT NULL,
     finished_at DATETIME(6) NULL,
     status ENUM('running','succeeded','failed') NOT NULL DEFAULT 'running',
     PRIMARY KEY (schedule, slot_start),
     KEY idx_schedule_run_schedule_finished (schedule, finished_at)
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
