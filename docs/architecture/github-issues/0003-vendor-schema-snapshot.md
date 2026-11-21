# Vendor a schema-only copy of latest.sql

| | |
|---|---|
| ID | 0003 |
| Phase / milestone | Phase 0: Stabilise and secure |
| Module | platform |
| Size | S |
| Labels | arch, phase:0, module:platform, type:chore, size:S, maintainer-only, repo:db-scripts |
| Depends on | none |
| Blocks | 0004, 0012, 0057 |
| Repos | mulearnbackend, db-scripts |

## Why

`db-scripts`, which owns the schema, is a private repository. Outside contributors can't build a local MySQL, and CI can't test against real tables. A schema-only copy of `db-scripts`' `latest.sql` in this repository fixes both. The schema is effectively public already through the models in `db/` ([ADR-014](../adr/ADR-014-db-scripts-single-schema-source.md)).

## Before you start

- This is maintainer-only: it needs read access to `db-scripts`.
- Read [Where the schema lives](../06-data-and-schema.md#where-the-schema-lives-and-how-it-changes).

## What to do

1. Take `latest.sql` from `db-scripts` `main` at a recorded commit.
2. Remove every data statement (`INSERT`, `UPDATE`, `DELETE`, `REPLACE`, `TRUNCATE`), keeping DDL only. Keep the `CREATE TABLE`, `ALTER TABLE`, index and constraint statements, in order.
   - Remove every comment as well: `--` and `#` lines, trailing `--` comments, and `/* */` blocks, including MySQL's `/*! */` version comments. Comments in `db-scripts` are written for its maintainers, so copy statements, never commentary.
   - Read every `COMMENT '…'` clause on tables and columns. Keep only those that describe the column itself.
3. Load the result into throwaway local `mysql:8.0` and `mysql:8.4` containers to confirm it loads cleanly. Never load it into a shared database.
4. Commit three files:
   - `schema/latest.sql`;
   - `schema/SOURCE`, holding the `db-scripts` commit SHA, its date and the date copied;
   - `schema/README.md`, which says what the file is, that it must never be edited by hand, and how to refresh it (the routine in `docs/architecture/github-issues/README.md`).

## Acceptance criteria

- [ ] `schema/latest.sql` loads without errors into fresh `mysql:8.0` and `mysql:8.4` containers.
- [ ] `grep -Ei "^(insert|update|delete|replace|truncate)" schema/latest.sql` finds nothing.
- [ ] `grep -nE '(^|[[:space:]])--([[:space:]]|$)|/\*|^[[:space:]]*#' schema/latest.sql` finds nothing.
- [ ] `schema/SOURCE` names the exact `db-scripts` commit.
- [ ] No credentials, hostnames, data or comments appear in the file, and a second maintainer has read it before merge.

## How to test

Load into a throwaway local container only:

```sh
docker run --rm -d --name schema-check -e MYSQL_ROOT_PASSWORD=local-only -e MYSQL_DATABASE=check mysql:8.4
docker exec -i schema-check sh -c 'until mysqladmin ping -uroot -plocal-only --silent; do sleep 1; done; mysql -uroot -plocal-only check' < schema/latest.sql
docker rm -f schema-check
```

## Out of scope

- Automating the refresh (later; the routine is manual for now).
- Retiring `schema.sql` (issue 0057).

## Notes for reviewers

Check that nothing beyond DDL left the private repository: no data, no comments, no table or column `COMMENT` that describes anything but the column.
