# Add the outbound HTTP client with timeouts and a circuit breaker

| | |
|---|---|
| ID | 0022 |
| Phase / milestone | Phase 1: Foundations |
| Module | building_blocks |
| Size | M |
| Labels | arch, phase:1, module:building_blocks, type:feature, size:M |
| Depends on | 0014, 0020 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

A slow outside service must never hold every request thread. All outbound calls go through one client with timeouts, bounded retries and a circuit breaker ([ADR-006](../adr/ADR-006-gunicorn-gthread-behind-nginx.md), [11-reliability-and-observability.md](../11-reliability-and-observability.md#timeouts-retries-and-circuit-breakers)).

## Before you start

- Issues 0014 and 0020 (typed config) must be merged.

## What to do

1. Create `building_blocks/http.py` with `get_client(name: str) -> Client`. Each name's settings come from typed config:
   - `base_url`;
   - `connect_timeout` (default 2 s) and `read_timeout` (default 5 s);
   - `retries` (default 2, idempotent methods only, jittered backoff);
   - `breaker_failures` (default 5) and `breaker_reset` (default 30 s).
2. The client wraps a `requests.Session`. When the breaker is open, calls raise `DependencyUnavailable` immediately, without trying the network. After `breaker_reset` seconds, one trial call is allowed through (half-open).
3. Add an import-linter contract: only `building_blocks.http` may import `requests` or `httpx` in new code.
4. Add tests with a fake transport (monkeypatch the session's `send`): timeouts are passed, retries happen only for GET/PUT/DELETE, the breaker opens after N failures and half-opens after the reset.

## Acceptance criteria

- [ ] All tests pass without network access.
- [ ] The import contract fails if new code imports `requests` directly.

## How to test

```sh
scripts/test.sh building_blocks/tests/
```

## Out of scope

- Moving existing legacy calls (as modules move).

## Notes for reviewers

Check that POST is never retried automatically.
