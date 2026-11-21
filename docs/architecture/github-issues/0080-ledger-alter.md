# Add the karma ledger table and the submission columns

| | |
|---|---|
| ID | 0080 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | contributions |
| Size | M |
| Labels | arch, phase:4, module:contributions, type:feature, size:M, maintainer-only, repo:db-scripts, needs-db-change |
| Depends on | 0049, 0051 |
| Blocks | 0081 |
| Repos | db-scripts |

## Why

The ledger needs its table, and submissions need the columns that make them idempotent: `source`, `source_ref`, `status` and `award_generation` ([ADR-004](../adr/ADR-004-karma-ledger.md), [06-data-and-schema.md](../06-data-and-schema.md#the-karma-ledger)).

## Before you start

- Maintainer-only: the work happens in the private `db-scripts` repository.
- Read [Where the schema lives, and how it changes](../06-data-and-schema.md#where-the-schema-lives-and-how-it-changes).
- Issue 0049 (stable alter ids) must be merged.
- Issue 0051 must also be merged.

## What to do

1. Write one expand alter in `db-scripts`, with a stable id and the standard header (`-- id:`, `-- requires:`, `-- online: yes`, `-- owner:`, `-- expand-contract: expand`), containing:

   ```sql
   CREATE TABLE karma_ledger_entry (
     id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
     entry_uuid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
     user_id VARCHAR(36) NOT NULL,
     submission_id VARCHAR(36) NULL,
     entry_type ENUM('award','reversal','penalty','adjustment','opening') NOT NULL,
     amount INT NOT NULL,
     source VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
     source_ref VARCHAR(191) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
     reverses_entry_id BIGINT UNSIGNED NULL,
     period CHAR(7) NOT NULL,
     member_path VARCHAR(191) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
     task_scope_path VARCHAR(191) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
     reason VARCHAR(255) NULL,
     created_by VARCHAR(36) NULL,
     created_at DATETIME(6) NOT NULL,
     UNIQUE KEY uq_karma_ledger_entry_source (source, source_ref),
     UNIQUE KEY uq_karma_ledger_entry_reverses (reverses_entry_id),
     UNIQUE KEY uq_karma_ledger_entry_uuid (entry_uuid),
     KEY idx_karma_ledger_entry_user_period (user_id, period),
     KEY idx_karma_ledger_entry_submission (submission_id),
     CONSTRAINT fk_karma_ledger_entry_ref_user FOREIGN KEY (user_id) REFERENCES `user` (id) ON DELETE CASCADE
   );
   ALTER TABLE karma_activity_log
     ADD COLUMN source VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NULL,
     ADD COLUMN source_ref VARCHAR(191) CHARACTER SET ascii COLLATE ascii_bin NULL,
     ADD COLUMN status ENUM('submitted','peer_approved','approved','rejected','reversed') NULL,
     ADD COLUMN award_generation INT NOT NULL DEFAULT 0,
     ADD UNIQUE KEY uq_karma_activity_log_source (source, source_ref),
     ALGORITHM=INPLACE, LOCK=NONE;
   -- add idx_karma_activity_log_task_message_id only if no index on task_message_id exists yet
   ```
2. Apply it to the shared environments through the migration runner after review: `dev`, then `staging`, then `production`.
3. Refresh the backend's `schema/latest.sql`, following the routine in the issues README.

## Acceptance criteria

- [ ] The alter is idempotent.
- [ ] It loads into a fresh `mysql:8.0` and `mysql:8.4` from `latest.sql`.
- [ ] `schema/latest.sql` in the backend contains the new tables.
- [ ] The `karma_activity_log` change runs online on a production-sized copy (record the timing).
- [ ] In the throwaway container, deleting a test user who has ledger entries succeeds. The user key is `CASCADE`, like `karma_activity_log.user` today, because both account-deletion paths still hard-delete users; it moves to `RESTRICT` in Phase 7 ([06-data-and-schema.md](../06-data-and-schema.md#the-karma-ledger)).

## How to test

Load `latest.sql` into a throwaway local MySQL container, run `SHOW CREATE TABLE` for each new table, and paste the output.

## Out of scope

- The backend models (the next issue in the chain).

## Notes for reviewers

Check the key columns are `ascii_bin` and every natural key has a `UNIQUE` constraint.
