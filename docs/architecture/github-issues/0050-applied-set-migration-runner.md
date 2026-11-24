# Track applied alters as a set in the migration runner

| | |
|---|---|
| ID | 0050 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | platform |
| Size | L |
| Labels | arch, phase:3, module:platform, type:feature, size:L, maintainer-only, repo:db-scripts |
| Depends on | 0049 |
| Blocks | 0051 |
| Repos | db-scripts |

## Why

Applying alters "by version" can lower the recorded schema version when an older branch's alter lands late, and nothing records which alters a database actually has. An applied set does ([ADR-040](../adr/ADR-040-db-scripts-safety-net.md)).

## Before you start

- Maintainer-only: the work happens in the private `db-scripts` repository.
- Read [Where the schema lives, and how it changes](../06-data-and-schema.md#where-the-schema-lives-and-how-it-changes).
- Issue 0049 must be merged.

## What to do

1. In `db-scripts`, build a migration runner (`dbmigrate`) that:
   - records every applied alter in a `schema_migration` table: id, checksum, applied at, applied by;
   - applies pending alters in `requires` order, one transaction-safe step at a time;
   - takes a named lock (`GET_LOCK`), so two runs can't overlap;
   - refuses an alter whose checksum changed after it was applied;
   - has `plan` (a dry run), `apply` and `baseline` (record ids without running them) commands.
2. Treat `system_setting` `db.version` as display-only: the runner never lowers it.
3. Write tests against a throwaway MySQL in `db-scripts` CI.

## Acceptance criteria

- [ ] Two concurrent `apply` runs: one waits, and nothing is applied twice.
- [ ] Applying an older id after a newer one works without lowering anything.
- [ ] `plan` prints exactly what `apply` would run.

## How to test

Run the runner's tests in `db-scripts` CI against a throwaway MySQL.

## Out of scope

- Running it on production (issue 0051).

## Notes for reviewers

Check the lock and checksum behaviour carefully: this tool writes DDL on production.
