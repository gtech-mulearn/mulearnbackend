# Add the k6 load-test scenarios

| | |
|---|---|
| ID | 0038 |
| Phase / milestone | Phase 2: Serving and runtime |
| Module | platform |
| Size | M |
| Labels | arch, phase:2, module:platform, type:chore, size:M |
| Depends on | 0033 |
| Blocks | 0047 |
| Repos | mulearnbackend |

## Why

The gunicorn cut-over is gated on load tests: a steady-state run at twice the modelled peak, and a slow-dependency run ([09-performance-and-caching.md](../09-performance-and-caching.md#load-tests)).

## Before you start

- Issue 0033 must be merged.

## What to do

1. Create `loadtest/k6/steady_state.js`: a mix of the busiest learner routes (profile, leaderboard, task list, interest groups) at a configurable rate for 30 minutes. Thresholds:
   - p95 < 300 ms;
   - errors < 0.5%.
2. Create `loadtest/k6/slow_dependency.js`: 60% load while a toxiproxy in front of the authserver adds 5 s of latency. Thresholds:
   - non-auth p99 < 1 s;
   - auth routes fail within 2.5 s with 503.
3. Create `loadtest/README.md`. It covers how to run against **staging only**, with tokens for seeded test users, never production. Results go in `docs/perf/<date>-<scenario>.md`.

## Acceptance criteria

- [ ] Both scripts run against a local environment at low rate without errors.
- [ ] The README says how to get test tokens for staging without using real users.

## How to test

Run `k6 run -e BASE_URL=http://localhost:8000 -e RATE=5 loadtest/k6/steady_state.js` against your local environment.

## Out of scope

- Running against staging (the maintainer does it before 0047).

## Notes for reviewers

Check that no script can be pointed at production by accident: refuse a `BASE_URL` matching the production host.
