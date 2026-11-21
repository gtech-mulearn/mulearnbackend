# Provision the evictable cache Redis and switch each environment

| | |
|---|---|
| ID | 0072 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | platform |
| Size | S |
| Labels | arch, phase:3, module:platform, type:chore, size:S, maintainer-only |
| Depends on | 0071 |
| Blocks | 0078 |
| Repos | mulearnbackend |

## Why

The code from issue 0071 only helps once each environment has a separate evictable cache.

## Before you start

- Maintainer-only: it needs infrastructure access.
- Issue 0071 must be merged.

## What to do

1. Provision a Redis for the cache in each environment with `maxmemory-policy allkeys-lru` and no persistence.
2. Set `REDIS_CACHE_URL` to it.
3. Set the existing instance's policy to `noeviction` and point `REDIS_STATE_URL` at it.
4. Deploy, then watch `evicted_keys` on the state instance for 7 days.

## Acceptance criteria

- [ ] `evicted_keys` stays at 0 on the state instance for 7 days.
- [ ] The cache hit ratio stays within 5 points of before.

## How to test

Record the before/after metrics on the issue.

## Out of scope

- Code changes.

## Notes for reviewers

This is reversible by pointing `REDIS_CACHE_URL` back at the old instance.
