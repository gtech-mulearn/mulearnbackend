# Record the production baseline of applied alters

| | |
|---|---|
| ID | 0051 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | platform |
| Size | S |
| Labels | arch, phase:3, module:platform, type:chore, size:S, maintainer-only, repo:db-scripts |
| Depends on | 0050 |
| Blocks | 0080 |
| Repos | db-scripts |

## Why

Before the runner manages production, it needs a baseline: the set of alters production already has, recorded without running them again.

## Before you start

- Maintainer-only: it needs production access.
- Issue 0050 must be merged.

## What to do

1. Compare production's `information_schema` with a database built from `latest.sql`, using the drift report once it exists, or a manual diff. Resolve or document every difference.
2. Run `dbmigrate baseline` on production. It records every alter in `latest.sql` as applied, without running any DDL.
3. From then on, apply every production alter through `dbmigrate apply`.

## Acceptance criteria

- [ ] `schema_migration` on production lists every alter in `latest.sql`.
- [ ] Every remaining difference has an owner, written in the known-drift list.

## How to test

Run `dbmigrate plan` on production after the baseline and confirm it shows nothing pending.

## Out of scope

- Fixing old drift (it is tracked in the known-drift list).

## Notes for reviewers

Do this outside caution windows, with a fresh backup.
