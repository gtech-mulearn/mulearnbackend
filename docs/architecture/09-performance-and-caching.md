# Performance and caching

How the backend is sized, what it promises, and what it caches. The decisions are:
- [ADR-009](adr/ADR-009-selective-cqrs-projections.md): read models;
- [ADR-019](adr/ADR-019-read-scaling-and-connections.md): connections and read scaling;
- [ADR-024](adr/ADR-024-leaderboards-and-period-totals.md): leaderboards;
- [ADR-026](adr/ADR-026-performance-budgets-in-ci.md): performance budgets;
- [ADR-043](adr/ADR-043-redis-cache-and-state.md): Redis roles;
- [ADR-045](adr/ADR-045-hot-path-serialization.md): serialization.

What limits performance today is in [02-current-state.md](02-current-state.md#performance-and-scalability-today).

## What limits performance

The first limits are not CPU. They are **database connections**, **query count per request** and **uncached aggregation on public reads**. Code layout does not change how many users the backend can serve. What changes it:
- many identical app processes behind a load balancer, with a fixed connection budget;
- a bounded query count per endpoint;
- precomputed read models for the expensive views;
- caches for hot public reads;
- workers for slow jobs.

## Targets

No user number is claimed until the capacity model has measured inputs and the load tests below have passed.

| Measure | Initial target (end of Phase 2) | Future target (when a scale tier's trigger fires) |
|---|---|---|
| Learner API latency | p50 ≤ 120 ms, p95 ≤ 300 ms, p99 ≤ 1 s | the same, at 10× the load |
| Leaderboard reads | p95 ≤ 150 ms at 2× peak | the same, from sorted sets if needed |
| Appraisal command | p95 ≤ 300 ms | the same |
| Approval → karma visible to others (event-fed) | p95 ≤ 60 s | p95 ≤ 10 s |
| `critical` queue age | p95 < 30 s, even during a bulk import | the same |
| Error rate (5xx) | < 0.5% per route family | < 0.1% |
| Availability (API) | 99.5% monthly | 99.9% |
| Recovery time (RTO) | in-region ≤ 2 h; loss of a whole region ≤ 24 h ([ADR-049](adr/ADR-049-deployment-platform-and-dr.md)) | in-region ≤ 1 h |
| Recovery point (RPO) | in-region ≤ 5 min (point-in-time recovery); loss of a whole region ≤ 24 h | in-region ≤ 1 min |
| Database query | p95 ≤ 50 ms on hot paths; no statement over 1 s on request paths | the same |

Reliability targets and alerting are in [11-reliability-and-observability.md](11-reliability-and-observability.md).

## The capacity model

The chain runs from users to requests, to busy threads, to CPU, to connections:

```text
peak_rps        = U × d × h × r / 3600 × b             users → requests
origin_rps      = peak_rps × (1 − c)                   c = share served by the edge and Redis
busy_threads    = origin_rps × S                       Little's law; S = mean service time
cpu_rps(node)   = vCPU × ρ / (S × f_cpu)               ρ = target utilisation; f_cpu = CPU share of S
thread_rps(node)= W × T × ρ / S
node_rps        = min(cpu_rps(node), thread_rps(node))
N_api           = max(2, ceil(origin_rps / node_rps) + 1)     +1 to survive losing a node

W (per node)    = min(vCPU + 1, floor(R_api / (N_api × T)), floor(0.75 × RAM_node / RSS_worker))
T               = 4
R_api           = floor(0.8 × max_connections) − C_other
C_other         = worker concurrency + relay loops + beat + authserver threads
                  + bot pool + scheduler pool + ops reserve
api_connections = N_api × W × T
```

- `U` is users.
- `d` is the daily active share.
- `h` is active hours per day.
- `r` is requests per active hour.
- `b` is the burst factor.

These inputs are hypotheses until two weeks of telemetry replace them ([11-reliability-and-observability.md](11-reliability-and-observability.md)). The model is re-run after every load test, and its numbers are recorded with the test result.

**The connection budget is the binding constraint.** Every process that talks to MySQL is counted. The total stays below 80% of `max_connections`, and gunicorn is sized from what is left ([ADR-006](adr/ADR-006-gunicorn-gthread-behind-nginx.md)). Persistent connections (`CONN_MAX_AGE = 60` with health checks) are turned on only after `gthread` has run one clean week. Until then each request still opens its own connection.

## Load tests

Load tests run with k6 against staging restored from a production-sized snapshot. They never run against production or the shared development database. Fault injection uses a proxy between the API and each dependency. Results are written up in `docs/perf/<date>-<scenario>.md`.

In every scenario, API connections stay within ±2 of `N × W × T`.

| Scenario | Load | Pass criteria | Gates |
|---|---|---|---|
| Mixed steady state | 2× modelled peak for 30 min | p95 ≤ 300 ms on learner routes; errors < 0.5%; connections flat; CPU ≤ 70% per node | The day-90 capacity statement |
| Slow dependency | 60% load with the authserver, then SMTP, then Discord delayed 5 s, one at a time | No connection growth; non-auth p99 ≤ 1 s; auth routes fail fast with 503, never a 30 s hang; recovery within 60 s | The gunicorn cut-over |
| Campus signup burst | 2,000 signups in 10 min from one source IP with distinct device ids | No 5xx; p99 ≤ 2 s; no duplicate `muid`; no 429 for distinct identifiers with campus event mode on | Rate-limit keys |
| Campus submission burst | 300 submissions in 2 min through the internal API, 3 appraisers each | No duplicate ledger entries; award p95 ≤ 60 s | The bot's move to the API |
| IST month boundary | 200 rps on boards across a simulated 18:30 UTC month flip | One recompute per board key; p95 ≤ 150 ms; no full scan of karma rows | Period totals and boards |
| Push fan-out | 100,000 sends at the configured budget | Home p95 ≤ 300 ms; `critical` age < 30 s; no duplicate deliveries | The notification pipeline |
| Discord storm and replay | 50 submissions/s from 2 bot instances; then a reconciler pass over a 48 h gap | No duplicate ledger entries; the reconciler converges within 15 min | The reconciler |
| Mobile retry storm | Every create POST sent 3 times with one `Idempotency-Key` | Exactly one effect; identical replies | Idempotency |

## Query budgets

- **Every list endpoint has a query-count test** at page size 1 and at the maximum page size, with `django_assert_max_num_queries`. The two counts must be equal: a count that grows with the page is an N+1 ([ADR-026](adr/ADR-026-performance-budgets-in-ci.md)).
- **Selectors declare their joins.** `select_related` and `prefetch_related` are declared in the selector. Method fields that query per row are not allowed on new endpoints ([ADR-045](adr/ADR-045-hot-path-serialization.md)).
- **Performance budgets are CI gates.** New endpoints are gated first, and legacy endpoints join through a ratchet.

## Read models

Expensive views get a read model in the same MySQL, fed by events and rebuildable from the source ([ADR-009](adr/ADR-009-selective-cqrs-projections.md)):

| Read model | Fed by | Read by | Rebuild |
|---|---|---|---|
| `karma_period_total` (user, IST period, scope path, karma) | `KarmaAwarded`, `KarmaReversed`, `KarmaPenalized`, `KarmaAdjusted`, batched on `projections` | leaderboards, profile rank | `rebuild_period_totals(period)` from the ledger |
| `organization` cached columns | `KarmaAwarded`, batched, or a beat job with a heartbeat | campus and organisation dashboards | recompute job |
| `learning_circle` cached columns | the same | learning-circle pages | recompute job |

- **Freshness.** Boards may be up to about 60 seconds stale, and that is documented on the endpoint.
- **When sorted sets come in.** Redis sorted sets for boards are added only when the trigger in [ADR-024](adr/ADR-024-leaderboards-and-period-totals.md) fires, and they are always rebuilt from the totals table.

**A query handler for a board** (target code):

```python
# modules/gamification/selectors/boards.py
from dataclasses import dataclass

from modules.gamification.data.models import PeriodTotalRow


@dataclass(frozen=True)
class BoardRow:
    rank: int
    user_id: str
    karma: int


def board(*, scope_path: str, period: str, cursor: int = 0, limit: int = 50) -> list[BoardRow]:
    rows = (PeriodTotalRow.objects
            .filter(period=period, scope_path=scope_path)
            .order_by("-karma", "user_id")
            .values_list("user_id", "karma")[cursor:cursor + min(limit, 100)])
    return [BoardRow(rank=cursor + i + 1, user_id=u, karma=k) for i, (u, k) in enumerate(rows)]
```

## Caching

There are two Redis roles ([ADR-043](adr/ADR-043-redis-cache-and-state.md)):
- **`redis-cache`** (`allkeys-lru`, no persistence) holds the Django `default` cache. Anything on it may vanish at any time.
- **`redis-state`** (`noeviction`) holds the Celery broker and the `state` alias: rate limits, locks, idempotency, grant caches and flag snapshots. Losing any of these would be a bug, so they are never put where they can be evicted.

**What is cached:**

| Data | Key | TTL | Invalidation | Consistency |
|---|---|---|---|---|
| Public board pages | `gam:board:{scope_type}:{scope_id}:{period}:{cursor}` | 60 s, served stale up to 300 s | expiry | up to about 60 s stale |
| Level thresholds | `gam:levels:v{n}` | 1 h | version bump when levels change | immediate after the bump |
| Voucher and coupon catalogue | `rew:catalogue:v{n}` | 10 min | version bump on edit | immediate after the bump |
| Public organisation and community pages | `org:page:{org_id}:v{n}` | 5 min | version bump on commit of an edit | immediate after the bump |
| A user's verified grants | `iam:grants:{user_id}` (on `state`) | 300 s | deleted on commit of any grant change | a revoked grant stops authorizing within 1 s |
| Public profile cards | `ppl:card:{muid}:v{n}` | 5 min | version bump on profile change | immediate after the bump |

**What is never cached:**
- **karma balances and ledger entries**, because a write reads them back;
- **the appraisal queue**, which is per principal and changes with every decision;
- **authorization decisions** (only the grant set is cached);
- **anything personal under a shared key.**

**Rules:**
- **One way in.** Cache reads go through `building_blocks.cache.get_or_compute`. Keys carry a version, so an invalidation is a version bump on commit, never a scan.
- **Stampedes are prevented** with probabilistic early recomputation and a short lock, so one request recomputes while the others serve the stale value.
- **HTTP caching.** Public reads send `Cache-Control: public, max-age=60, stale-while-revalidate=300` and an ETag. Authenticated responses are `private, no-store` ([07-api-standards.md](07-api-standards.md)).
- **CDN.** Static assets and media are served from the CDN and R2, never by the app servers.

**A cached read with a stampede guard** (target code):

```python
# building_blocks/cache.py
import math
import random
import time

from django.core.cache import caches


def get_or_compute(key: str, compute, *, ttl: int, stale_ttl: int = 0, beta: float = 1.0, alias: str = "default"):
    cache = caches[alias]
    hit = cache.get(key)                       # stored as (value, computed_at, cost_seconds)
    now = time.time()
    if hit is not None:
        value, computed_at, cost = hit
        age = now - computed_at
        # XFetch: recompute early with a probability that grows as expiry approaches
        if age < ttl and age - cost * beta * math.log(random.random() or 1e-9) < ttl:
            return value
        if age < ttl + stale_ttl and not cache.add(f"{key}:lock", 1, timeout=max(1, int(cost * 2))):
            return value                       # someone else is recomputing; serve stale
    start = time.time()
    value = compute()
    cache.set(key, (value, time.time(), time.time() - start), timeout=ttl + stale_ttl)
    return value
```
