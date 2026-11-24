# Make persistent database connections configurable

| | |
|---|---|
| ID | 0046 |
| Phase / milestone | Phase 2: Serving and runtime |
| Module | platform |
| Size | S |
| Labels | arch, phase:2, module:platform, type:feature, size:S |
| Depends on | 0033 |
| Blocks | 0047 |
| Repos | mulearnbackend |

## Why

`CONN_MAX_AGE = 0` opens a new database connection per request. Under gunicorn `gthread`, persistent connections with health checks cut that cost, but only once threaded serving has proven stable ([ADR-019](../adr/ADR-019-read-scaling-and-connections.md)).

## Before you start

- Issue 0033 must be merged.

## What to do

1. Make `CONN_MAX_AGE` configurable through typed config, with default `0` (no change), and set `CONN_HEALTH_CHECKS = True`.
2. Add a boot check that refuses `CONN_MAX_AGE > 0` when the process runs under ASGI, where connections are per thread and leak.
3. Document in `deploy/README.md`: set `CONN_MAX_AGE=60` only after gunicorn `gthread` has run one clean week in that environment.

## Acceptance criteria

- [ ] With no setting, behaviour is unchanged.
- [ ] `CONN_MAX_AGE=60` under gunicorn reuses connections (shown in a local test with the MySQL tier).
- [ ] The ASGI guard refuses to boot with persistent connections.

## How to test

```sh
scripts/test.sh building_blocks/tests/
```

## Out of scope

- Changing any environment's value (the maintainer does that after the clean week).

## Notes for reviewers

Check the ASGI guard can't be bypassed by setting the value after boot.
