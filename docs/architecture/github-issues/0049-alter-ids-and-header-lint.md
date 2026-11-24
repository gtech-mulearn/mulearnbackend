# Give alters stable ids and lint their headers

| | |
|---|---|
| ID | 0049 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | platform |
| Size | M |
| Labels | arch, phase:3, module:platform, type:chore, size:M, maintainer-only, repo:db-scripts |
| Depends on | none |
| Blocks | 0050, 0052, 0058, 0066, 0073, 0080, 0089 |
| Repos | db-scripts |

## Why

Today alters are numbered by version, and the numbers collide: parallel branches have produced two alters with the same number more than once. The schema version is one number that can go backwards. Stable ids, with a header that says what each alter needs, let the backend declare which alters it requires ([ADR-040](../adr/ADR-040-db-scripts-safety-net.md)).

## Before you start

- Maintainer-only: the work happens in the private `db-scripts` repository.
- Read [Where the schema lives, and how it changes](../06-data-and-schema.md#where-the-schema-lives-and-how-it-changes).

## What to do

1. Adopt stable ids for new alters: `YYYYMMDD-HHMM-<slug>`, assigned when the alter merges. Existing versioned alters keep their file names as their ids.
2. Require this header in every new alter:

   ```sql
   -- id: 20261221-1015-outbox-tables
   -- requires: <id or none>
   -- online: yes|no
   -- owner: <module>
   -- expand-contract: expand|contract
   ```
3. Add a lint script and a CI check in `db-scripts`. It fails on a missing or invalid header, a duplicate id, or a `requires` naming an unknown id.
4. Document the format in `db-scripts`' `agent.md`.

## Acceptance criteria

- [ ] The lint fails on a fixture with a duplicate id and on one with a missing header.
- [ ] Every alter added from now on passes the lint.

## How to test

Run the lint in `db-scripts` CI on a pull request containing one valid and one invalid fixture alter.

## Out of scope

- Renaming existing alters.
- The runner (issue 0050).

## Notes for reviewers

This changes how every future schema change is named. Announce it to everyone who writes alters.
