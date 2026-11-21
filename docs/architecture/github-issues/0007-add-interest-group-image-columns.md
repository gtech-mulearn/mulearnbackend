# Add the interest-group image key columns to db-scripts

| | |
|---|---|
| ID | 0007 |
| Phase / milestone | Phase 0: Stabilise and secure |
| Module | communities |
| Size | S |
| Labels | arch, phase:0, module:communities, type:chore, size:S, maintainer-only, repo:db-scripts, needs-db-change |
| Depends on | none |
| Blocks | none |
| Repos | db-scripts |

## Why

`db/task.py` `InterestGroup` maps two columns, `cover_image_key` and `icon_image_key` (`CharField(max_length=255, null=True, blank=True)`). No `db-scripts` alter creates them, so a fresh database built from `db-scripts` doesn't match the model, and promoting `dev` would break on those columns.

## Before you start

- This is maintainer-only: it needs write access to `db-scripts`.
- Read `db-scripts`' `agent.md` and [How a contributor changes the schema](../06-data-and-schema.md#where-the-schema-lives-and-how-it-changes).

## What to do

1. In `db-scripts`, write an expand alter that adds, only if absent (use the repository's conditional-DDL pattern):

   ```sql
   ALTER TABLE interest_group
     ADD COLUMN cover_image_key VARCHAR(255) NULL,
     ADD COLUMN icon_image_key  VARCHAR(255) NULL;
   ```
2. Append it to `latest.sql` as the repository's process requires.
3. Check the open `db-scripts` pull requests for alter numbering, and assign the number at merge.
4. After it is applied, refresh `schema/latest.sql` in the backend (the routine in the issues README).

## Acceptance criteria

- [ ] The alter is idempotent: running it twice is a no-op.
- [ ] A database built from `latest.sql` has both columns, and the `InterestGroup` model reads and writes them.
- [ ] The backend's `schema/latest.sql` is refreshed.

## How to test

Load `latest.sql` into a throwaway local MySQL container and run `SHOW COLUMNS FROM interest_group LIKE '%image_key'`. Expect two rows.

## Out of scope

- The interest-group image upload contract, which is coordinated with #3145.

## Notes for reviewers

This is an expand-only change. Check that the column types match the model exactly.
