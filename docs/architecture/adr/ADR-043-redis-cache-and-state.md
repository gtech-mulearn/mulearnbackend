# ADR-043: Redis: an evictable cache and a non-evicting state store

Status: Accepted (new on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-21)
Implementation status at dev 7fd66060: not started. One Redis host serves the channel layer, the cache (DB 1) and the Celery broker (DB 2).

## Context

When the cache, the broker and security-relevant counters share one Redis instance and one
eviction policy, memory pressure can evict queued tasks or rate-limit counters along with
ordinary cache entries.

## Options considered

- **One instance with `noeviction`:** the cache errors when it is full.
- **One instance with LRU:** broker messages and counters can be evicted.
- **Two instances.**

## Decision

| | `redis-cache` | `redis-state` |
|---|---|---|
| Eviction policy | `allkeys-lru`, no persistence | `noeviction`, with persistence |
| Holds | The Django `default` cache only | The Celery broker and the Django `state` cache alias |
| Key prefixes | One per service | One per service |
| Client timeouts | Connect 0.25 s, operation 0.5 s | Same |

- **Storage is chosen by cache alias, not by instance.** Both services get a `state` alias. It
  holds:
  - limiters and throttles;
  - locks;
  - replay guards;
  - sessions;
  - flag snapshots;
  - delivery budgets;
  - later, sorted-set boards.
- Anything whose loss is a security or correctness problem never uses `default`, and a CI check
  enforces this.
- **Stampede-safe compute:** `building_blocks.cache.get_or_compute(key, ttl, fn, stale_ttl=...)`
  serves stale data while one caller recomputes under a short lock.
- **Engine:** Valkey or Redis 7.x.

**Degraded modes:**

| What is down | Behaviour |
|---|---|
| Cache | Treated as a miss. Shed the public role if the database budget is threatened. |
| Broker | Outbox rows accumulate with no loss. `safe_enqueue()` falls back to the outbox. |
| Limiters | Authentication limiters use an in-process fallback; others fail open. |
| Flags | The last good snapshot, then declared defaults. |

### Refinements (2026-11-21)

- The cache version counters (`ver:*`) and the read-your-writes pins live on the `state` alias, so an eviction can never serve a stale permission entry.

## Consequences

- Cache pressure can't drop tasks or reset counters.
- Two instances to size and monitor. A replica for the state store is deferred.

## Revisit when

- State-store memory exceeds 70%, or a broker incident occurs.

## Related ADRs

[ADR-036](ADR-036-rate-limiting.md), [ADR-041](ADR-041-transactions-and-consistency.md), [ADR-042](ADR-042-background-work-celery.md)
