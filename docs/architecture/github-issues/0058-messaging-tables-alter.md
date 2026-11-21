# Create the outbox, inbox, dead-letter and idempotency tables

| | |
|---|---|
| ID | 0058 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | building_blocks |
| Size | M |
| Labels | arch, phase:3, module:building_blocks, type:feature, size:M, maintainer-only, repo:db-scripts, needs-db-change |
| Depends on | 0049 |
| Blocks | 0059 |
| Repos | db-scripts |

## Why

The outbox, the inbox, dead letters and idempotency records need their tables before any event can be published ([ADR-005](../adr/ADR-005-transactional-outbox.md), [05-events-and-background-work.md](../05-events-and-background-work.md)).

## Before you start

- Maintainer-only: the work happens in the private `db-scripts` repository.
- Read [Where the schema lives, and how it changes](../06-data-and-schema.md#where-the-schema-lives-and-how-it-changes).
- Issue 0049 (stable alter ids) must be merged.

## What to do

1. Write one expand alter in `db-scripts`, with a stable id and the standard header (`-- id:`, `-- requires:`, `-- online: yes`, `-- owner:`, `-- expand-contract: expand`), containing:

   ```sql
   CREATE TABLE outbox_event (
     id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
     event_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
     type VARCHAR(191) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
     source VARCHAR(64) NOT NULL,
     subject VARCHAR(191) NOT NULL,
     envelope JSON NOT NULL,
     occurred_at DATETIME(6) NOT NULL,
     claimed_until DATETIME(6) NULL,
     published_at DATETIME(6) NULL,
     attempts INT NOT NULL DEFAULT 0,
     relay_partition TINYINT UNSIGNED AS (CRC32(subject) % 16) STORED,
     UNIQUE KEY uq_outbox_event_event_id (event_id),
     KEY idx_outbox_event_due (published_at, claimed_until, id)
   );
   CREATE TABLE inbox_record (
     consumer VARCHAR(191) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
     event_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
     processed_at DATETIME(6) NOT NULL,
     PRIMARY KEY (consumer, event_id),
     KEY idx_inbox_record_processed_at (processed_at)
   );
   CREATE TABLE dead_letter (
     id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
     consumer VARCHAR(191) NOT NULL,
     event_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
     envelope JSON NOT NULL,
     error TEXT NOT NULL,
     attempts INT NOT NULL,
     created_at DATETIME(6) NOT NULL,
     resolved_at DATETIME(6) NULL,
     KEY idx_dead_letter_consumer_open (consumer, resolved_at)
   );
   CREATE TABLE idempotency_record (
     idem_key VARCHAR(191) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
     scope VARCHAR(191) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
     request_hash CHAR(64) NOT NULL,
     status_code SMALLINT NULL,
     response JSON NULL,
     expires_at DATETIME(6) NOT NULL,
     PRIMARY KEY (scope, idem_key),
     KEY idx_idempotency_record_expires_at (expires_at)
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
