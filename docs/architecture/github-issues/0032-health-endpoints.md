# Add live and ready health endpoints with a drain flag

| | |
|---|---|
| ID | 0032 |
| Phase / milestone | Phase 2: Serving and runtime |
| Module | building_blocks |
| Size | M |
| Labels | arch, phase:2, module:building_blocks, type:feature, size:M |
| Depends on | 0014 |
| Blocks | 0033, 0035, 0037, 0052 |
| Repos | mulearnbackend |

## Why

A load balancer needs to know when a process can take traffic, and a deploy needs to drain a node before stopping it. Readiness must describe this process only: one bad dependency shouldn't take the whole fleet out of rotation ([ADR-006](../adr/ADR-006-gunicorn-gthread-behind-nginx.md), [10-infrastructure-and-deployment.md](../10-infrastructure-and-deployment.md#containers)).

## Before you start

- Issue 0014 must be merged.

## What to do

1. Create `building_blocks/health/views.py` with two views:
   - `live`: always 200 `{"status": "ok"}`;
   - `ready`: 503 if draining. Otherwise it runs `SELECT 1` on the default database and a `get` on the cache, and returns 503 `unavailable` if either fails, else 200 `ready`.
2. Create `building_blocks/health/drain.py`. `is_draining()` is true when the file at `settings.DRAIN_FLAG_PATH` (default `/tmp/mulearn-drain`) exists.
3. Route `/healthz/live` and `/healthz/ready` at the root URLconf, outside `/api/v1/`, with no authentication and no logging of successful calls.
4. Add tests: live is always 200; ready is 503 when the drain file exists, 503 when the database check raises, and 200 otherwise.

## Acceptance criteria

- [ ] Both endpoints answer within 50 ms locally.
- [ ] Touching the drain file makes `ready` return 503 within one request.
- [ ] Neither endpoint needs a token.

## How to test

```sh
scripts/test.sh building_blocks/tests/
```

## Out of scope

- Schema-version checks in readiness. Those belong to deploy pre-flight and boot (issue 0052), not readiness.

## Notes for reviewers

Readiness must not check anything outside this process.
