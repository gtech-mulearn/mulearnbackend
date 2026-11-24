# Add gunicorn gthread and nginx configuration

| | |
|---|---|
| ID | 0033 |
| Phase / milestone | Phase 2: Serving and runtime |
| Module | platform |
| Size | M |
| Labels | arch, phase:2, module:platform, type:feature, size:M |
| Depends on | 0032 |
| Blocks | 0034, 0035, 0038, 0046 |
| Repos | mulearnbackend |

## Why

Production runs Django's development server through `manage.py runserver` / `daphne`. It has no worker bounds, no timeouts and no graceful drain. gunicorn `gthread` behind nginx, sized from the connection budget, fixes all three ([ADR-006](../adr/ADR-006-gunicorn-gthread-behind-nginx.md)).

## Before you start

- Issue 0032 must be merged.
- Read the sizing formula and the timeout table in [ADR-006](../adr/ADR-006-gunicorn-gthread-behind-nginx.md).

## What to do

1. Add `gunicorn` (pinned) to `requirements.txt`.
2. Create `gunicorn.conf.py` with these settings:
   - `worker_class = "gthread"`, `threads = 4`, `workers` from the `WEB_WORKERS` environment variable (default 2);
   - `timeout = 35`, `graceful_timeout = 25`;
   - `max_requests = 2000`, `max_requests_jitter = 200`;
   - `bind = "0.0.0.0:8000"`, access logs to stdout.
3. Create `deploy/nginx/mulearn.conf`:
   - `client_max_body_size 10m`;
   - `proxy_read_timeout 10s` for `/api/`, and `30s` for admin paths (`/api/v1/dashboard/` admin routes, listed in a `map`);
   - `keepalive_timeout 40s`;
   - forward `X-Request-Id` and the client address headers.
4. Add an in-app request deadline of 9 s (29 s on admin paths). Use a middleware that sets a per-request deadline and makes the database cursor apply `MAX_EXECUTION_TIME` to SELECTs.
5. Add a CI step that starts gunicorn with this config against SQLite and calls `/healthz/live`.

## Acceptance criteria

- [ ] `gunicorn -c gunicorn.conf.py mulearnbackend.wsgi` serves `/healthz/live` locally.
- [ ] A request that sleeps 12 s on an app path is cut off by nginx at 10 s in a local test with the nginx config.
- [ ] Production is unchanged (the cut-over is issue 0047).

## How to test

```sh
scripts/test.sh building_blocks/tests/
```

Then run `gunicorn -c gunicorn.conf.py mulearnbackend.wsgi` with the SQLite environment and `curl localhost:8000/healthz/live`.

## Out of scope

- Switching any environment to gunicorn (issues 0045 and 0047).
- Persistent connections (issue 0046).

## Notes for reviewers

Check that the timeouts are aligned, so a client retry never overlaps a request that is still running.
