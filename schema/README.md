# schema/

`latest.sql` is a **schema-only copy** of `latest.sql` in `db-scripts`, the private repository that owns the database schema. It exists so contributors can build a local MySQL and CI can test against real tables ([ADR-014](../docs/architecture/adr/ADR-014-db-scripts-single-schema-source.md)).

- **What it contains:** the `CREATE TABLE`, `ALTER TABLE` and `CREATE INDEX` statements, in their original order. There is no data, and no comments. Table and column `COMMENT` clauses are kept only where they describe the column itself.
- **Where it came from:** `SOURCE` records the `db-scripts` commit, its date and the date it was copied.
- **Never edit it by hand.** Schema changes are made in `db-scripts`, as alters. This file is then refreshed from there.
- **Load it only into a throwaway local database,** for example a fresh `mysql:8.4` container. Never load it into a shared database.

## Loading it

Turn binary logging off for the loading session:

```sh
mysql --init-command="SET SESSION sql_log_bin=0" -uroot -p <database> < schema/latest.sql
```

One statement adds `level.level_system_id` with `DEFAULT (UUID())`. MySQL 8 refuses `ALTER TABLE … ADD COLUMN` with a non-deterministic default while binary logging is on (`ERROR 1674 … unsafe because it uses a system function`), and binary logging is on by default in MySQL 8, including the official containers. `sql_log_bin=0` affects only that session. The statement is copied as is from `db-scripts`, so this file isn't changed to work around it.

## Refreshing it

A maintainer with access to `db-scripts` refreshes it after alters merge there. Follow the routine in [Refreshing the vendored schema](../docs/architecture/github-issues/README.md#refreshing-the-vendored-schema), which uses the rules of issue 0003:
1. Take `latest.sql` from `db-scripts` `main`.
2. Remove every data statement (`INSERT`, `UPDATE`, `DELETE`, `REPLACE`, `TRUNCATE`) and every comment (`--`, `#`, `/* */`, including `/*! */`).
3. Check the result. Both commands must print nothing:

   ```sh
   grep -Ei "^(insert|update|delete|replace|truncate)" schema/latest.sql
   grep -nE '(^|[[:space:]])--([[:space:]]|$)|/\*|^[[:space:]]*#' schema/latest.sql
   ```

4. Update `SOURCE`, and have a second maintainer read the diff before merging.
