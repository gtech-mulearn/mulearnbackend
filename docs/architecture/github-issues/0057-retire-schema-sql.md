# Retire schema.sql

| | |
|---|---|
| ID | 0057 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | platform |
| Size | S |
| Labels | arch, phase:3, module:platform, type:chore, size:S |
| Depends on | 0003, 0053 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

`schema.sql` is a hand-kept second description of the schema next to `db-scripts`, and it drifts. Once parity tests check models against the vendored schema, it has no purpose left.

## Before you start

- Issues 0003 and 0053 must be merged.

## What to do

1. Search the repository for references to `schema.sql` (docs, scripts, compose files) and point each one at `schema/latest.sql`.
2. Delete `schema.sql`.

## Acceptance criteria

- [ ] `git grep -n "schema.sql"` finds only references to `schema/latest.sql`.
- [ ] CI passes.

## How to test

```sh
scripts/test.sh tests/
```

## Out of scope

- Anything about `db-scripts` itself.

## Notes for reviewers

Check nothing in deploy scripts loaded `schema.sql`.
