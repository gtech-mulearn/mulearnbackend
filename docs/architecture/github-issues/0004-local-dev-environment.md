# Add a one-command local development environment

| | |
|---|---|
| ID | 0004 |
| Phase / milestone | Phase 0: Stabilise and secure |
| Module | platform |
| Size | M |
| Labels | arch, phase:0, module:platform, type:feature, size:M |
| Depends on | 0002, 0003 |
| Blocks | 0008, 0012, 0061, 0064, 0068 |
| Repos | mulearnbackend |

## Why

A contributor should be able to clone the repository and run the whole backend locally with one command, without access to any shared database. With the vendored schema (0003), a local MySQL can be built from scratch.

## Before you start

- Issue 0003 must be merged.
- Read [Environments](../10-infrastructure-and-deployment.md#environments) and the local Compose example in [10-infrastructure-and-deployment.md](../10-infrastructure-and-deployment.md#examples).
- Note that `db/apps.py` `check_system_user_exists` refuses to start unless a user with id `SYSTEM_ADMIN_ID` exists.
- Issue 0002 must also be merged.

## What to do

1. Create `docker-compose.local.yml`, separate from the production `docker-compose.yml`. It has:
   - `mysql` (`mysql:8.4`), loading `schema/latest.sql` into `mulearn` and `test_mulearn` through an init script `scripts/local-db-init.sh`;
   - `redis-cache` (`allkeys-lru`) and `redis-state` (`noeviction`);
   - `web` (`python manage.py runserver 0.0.0.0:8000`);
   - `worker`;
   - `beat` (with its schedule file on a named volume).

   Every service reads `.env.local` (`env_file`). Commands run on the host, such as `scripts/test.sh`, read `.env`.

   Publish ports only on `127.0.0.1`.
2. Create `scripts/seed-system-user.sql`: one `INSERT IGNORE` of a system user whose id equals `SYSTEM_ADMIN_ID` in `.env.local.example`. It is a local-only seed, with no real data. `scripts/local-db-init.sh` applies it to both `mulearn` and `test_mulearn` after loading the schema, because the backend refuses to start against a database without that user.
3. Create `.env.local.example` with every setting the app needs at startup, set to safe local values:
   - `DATABASE_HOST=mysql`, `DATABASE_NAME=mulearn`;
   - the Redis hosts;
   - dummy values for external services.

   Never use real secrets.
4. Make sure `.env.local` is ignored by git.

## Acceptance criteria

- [ ] `cp .env.local.example .env.local && docker compose -f docker-compose.local.yml up -d` brings everything up on a clean machine.
- [ ] `curl -s localhost:8000/api/v1/public/` (or any public route) returns an envelope, not a startup error.
- [ ] `scripts/test.sh --mysql` connects to `test_mulearn` and the guard allows it.
- [ ] No port is published on `0.0.0.0`.

## How to test

```sh
cp .env.local.example .env.local
docker compose -f docker-compose.local.yml up -d
scripts/test.sh tests/test_db_guard.py
```

## Out of scope

- The relay service (added with issue 0061).
- Seeding realistic data.

## Notes for reviewers

Check that the init script can't run against anything except the local container, and that `.env.local.example` contains no real secrets.
