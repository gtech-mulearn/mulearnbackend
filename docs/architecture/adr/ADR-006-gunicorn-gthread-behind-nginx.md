# ADR-006: gunicorn `gthread` behind nginx and a load balancer

Status: Accepted (amended on 2026-11-21: threaded workers from day one; supersedes the staging in ADR-025)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. `docker-compose.yml` starts `manage.py runserver` and `entrypoint.sh` starts `daphne`; `CONN_MAX_AGE` is 0.

## Context

The application server must bound concurrency, database connections and request time, and it
must drain gracefully on deploy. The code already runs each request on its own thread, so thread
safety is already exercised. Sync workers would cut concurrency per node while outbound calls
still sit on some request paths, and campus bursts land exactly there.

## Options considered

- **gunicorn with sync workers:** simple, but low concurrency per GB of RAM.
- **gunicorn with `gthread`, sized from the connection budget.**
- **ASGI (uvicorn or Daphne):** the code is synchronous, so the ORM still needs a thread per
  request, and nothing is gained.

## Decision

**Server.** gunicorn `gthread` with `T = 4` threads and `W` workers per node, behind nginx on
each node and a health-checked AWS Application Load Balancer across at least two Availability
Zones.

**Sizing formula** ([ADR-019](ADR-019-read-scaling-and-connections.md) defines the budget terms):

```
R_api = floor(0.8 × max_connections)
        − (worker concurrency + relay loops + beat + authserver workers × threads
           + other services' pools + ops reserve)
W per node = min(vCPU + 1, floor(R_api / (nodes × T)), floor(0.75 × RAM / worker RSS))
```

**Raising `T` beyond 4** requires that every outbound call goes through `building_blocks.http`
with a timeout.

**Aligned timeouts.**

| Layer | App | Admin |
|---|---|---|
| nginx `proxy_read_timeout`, per path | 10 s | 30 s |
| Load balancer idle timeout (one value for the whole balancer) | 35 s | 35 s |
| In-app deadline | 9 s | 29 s |
| gunicorn `timeout` (backstop) | 35 s | 35 s |

**Other settings:** `graceful_timeout` 25 s, `max_requests` 2000 with jitter, a 10 MB body limit
(media goes direct to object storage), and Django upload memory limits of 5 MB and 2.5 MB.

**Drain order on deploy:** drain flag → readiness returns 503 → the balancer deregisters the
node → SIGTERM → graceful exit.

**Guards:**
- Boot refuses persistent DB connections under ASGI.
- The authserver also runs `gthread`, with at least 3 workers × 4 threads, since every login
  passes through it.

### Refinements (2026-11-21)

- The load balancer's idle timeout applies to the whole balancer, so it is 35 s, and the 10 s and 30 s limits are enforced per path in nginx. nginx `keepalive_timeout` is 40 s, above the balancer's idle timeout.
- gunicorn `preload_app` stays off until the database query at application start-up (`db/apps.py` `check_system_user_exists`, called from `AppConfig.ready()`) moves out ([ADR-048](ADR-048-typed-configuration.md)).

## Consequences

- Concurrency and connections become fixed, budgeted numbers.
- Module-level state must be thread-safe, as it already must be today.
- One load test, with slow-dependency injection, runs before cut-over.

## Revisit when

- Load tests show GIL contention at p95 (add workers instead of threads).

## Related ADRs

[ADR-019](ADR-019-read-scaling-and-connections.md), [ADR-023](ADR-023-one-image-several-roles.md), [ADR-025](ADR-025-serving-model-evolution.md), [ADR-039](ADR-039-retire-channels-and-daphne.md), [ADR-049](ADR-049-deployment-platform-and-dr.md)
