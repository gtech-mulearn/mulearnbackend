# Split Redis into cache and state aliases

| | |
|---|---|
| ID | 0071 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | platform |
| Size | M |
| Labels | arch, phase:3, module:platform, type:feature, size:M |
| Depends on | 0020 |
| Blocks | 0072, 0074, 0090 |
| Repos | mulearnbackend |

## Why

One Redis host carries the cache, the Celery broker and the channel layer, with no eviction policy. Losing a cache key is fine; losing a rate-limit counter, a lock or a broker message is a bug. They need separate roles ([ADR-043](../adr/ADR-043-redis-cache-and-state.md)).

## Before you start

- Issue 0020 (typed config) must be merged.
- Read the `CACHES` and Celery broker settings in `mulearnbackend/settings.py`.

## What to do

1. Add the settings `REDIS_CACHE_URL` and `REDIS_STATE_URL`. Both default to today's host and databases, so nothing changes until they are set.
2. Define two cache aliases:
   - `default` (`REDIS_CACHE_URL`, key prefix `be`);
   - `state` (`REDIS_STATE_URL`, key prefix `be-state`).
   Give both socket timeouts.
3. Point the Celery broker at `REDIS_STATE_URL`.
4. Find every cache use that is really state (locks, rate limits, budgets, idempotency) with `git grep -n "cache\." -- api utils mu_celery`, and move each to `caches["state"]`. List them in the pull request.
5. Add a startup warning if the `state` instance's `maxmemory-policy` isn't `noeviction`.

## Acceptance criteria

- [ ] With no new settings, behaviour is unchanged.
- [ ] Every lock, limiter and budget uses the `state` alias.
- [ ] The warning fires against a local Redis with `allkeys-lru` configured as state.

## How to test

```sh
scripts/test.sh tests/
```

## Out of scope

- Provisioning the new Redis (issue 0072).

## Notes for reviewers

Check the list of moved call sites. A lock left on the evictable cache is the bug this prevents.
